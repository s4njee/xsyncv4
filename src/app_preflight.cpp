#include "app_preflight.h"
#include "revision.h"
#include <algorithm>
#include <cerrno>
#include <climits>
#include <fcntl.h>
#include <limits>
#include <system_error>
#include <unistd.h>
#include <sys/statvfs.h>
#ifdef __APPLE__
#include <sys/attr.h>
#include <sys/mount.h>
#else
#include <linux/fs.h>
#include <sys/ioctl.h>
#include <sys/vfs.h>
#endif

namespace app_preflight {
using app_json::Value;
namespace {
Value text(const std::string& s) { return {Value::String,s,{}, {}}; }
Value number(u64 n) { return text(std::to_string(n)); }
Value boolean(bool b) { return {Value::Bool,b ? "true" : "false",{}, {}}; }
Value object() { return {Value::Object,{},{},{}}; }
u64 decimal(const Value& v,u64 maximum = UINT64_MAX) {
  const auto& s = v.string();
  if (s.empty() || s.size() > 20) throw std::runtime_error("invalid preflight decimal string");
  u64 n = 0;
  for (char c : s) {
    if (c < '0' || c > '9' || n > maximum/10 || (n == maximum/10 && u64(c-'0') > maximum%10))
      throw std::runtime_error("preflight decimal out of range");
    n = n*10+c-'0';
  }
  return n;
}
u64 add(u64 a,u64 b) {
  if (b > UINT64_MAX-a) throw std::runtime_error("preflight budget overflow");
  return a+b;
}
Value product(u64 a,u64 b) { return a && b > UINT64_MAX/a ? Value{} : number(a*b); }
Value revision(const DestinationRevision& r) {
  auto v = object();
  v.object = {{"exists",boolean(true)},{"device",number(r.device)},{"inode",number(r.inode)},{"links",number(r.links)},
    {"mode",number(r.mode)},{"uid",number(r.uid)},{"gid",number(r.gid)},{"flags",number(r.flags)},
    {"size",text(std::to_string(r.size))},{"mtime_seconds",text(std::to_string(r.mtime))},{"mtime_nanoseconds",number(r.mtime_ns)},
    {"ctime_seconds",text(std::to_string(r.ctime))},{"ctime_nanoseconds",number(r.ctime_ns)}};
  return v;
}
struct FD { int fd; ~FD() { if (fd >= 0) close(fd); } };
[[noreturn]] void fail(int error) { throw std::system_error(error,std::generic_category(),"destination preflight"); }
}

Value parse(const Value& request) {
  for (const auto& [key,value] : request.object)
    if (key != "id" && key != "op" && key != "endpoint" && key != "space") throw std::runtime_error("unsupported preflight field");
  if (!request.object.count("space")) return {};
  auto space = request.at("space");
  if (space.kind != Value::Object) throw std::runtime_error("preflight space must be an object");
  for (const auto& [key,value] : space.object)
    if (key != "regular_file_sizes" && key != "jobs" && key != "retained_logical_bytes") throw std::runtime_error("unsupported preflight budget field");
  const auto& sizes = space.at("regular_file_sizes");
  if (sizes.kind != Value::Array || sizes.array.size() > 100000) throw std::runtime_error("invalid preflight file budget");
  u64 total = 0;
  for (const auto& size : sizes.array) total = add(total,decimal(size,INT64_MAX));
  if (space.object.count("jobs") && decimal(space.at("jobs"),64) == 0) throw std::runtime_error("preflight jobs must be 1 to 64");
  u64 retained = space.object.count("retained_logical_bytes") ? decimal(space.at("retained_logical_bytes")) : 0;
  (void)add(total,retained);
  return space;
}

Value inspect(const std::string& path,const Value& space) {
  FD root{open(path.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)};
  if (root.fd < 0) fail(errno);
  struct stat before, after, named;
  if (fstat(root.fd,&before)) fail(errno);
  auto original = DestinationRevision::from(before);
  auto result = object(), capacity = object(), names = object(), metadata = object();
  capacity.object = {{"total_bytes",{}},{"free_bytes",{}},{"available_bytes",{}},{"allocation_unit_bytes",{}},{"native_error",{}}};
  Value read_only, access, type;
  struct statvfs volume{};
  if (!fstatvfs(root.fd,&volume)) {
    u64 unit = volume.f_frsize ? volume.f_frsize : volume.f_bsize;
    if (unit) {
      capacity.object["total_bytes"] = product(volume.f_blocks,unit);
      capacity.object["free_bytes"] = product(volume.f_bfree,unit);
      capacity.object["available_bytes"] = product(volume.f_bavail,unit);
      capacity.object["allocation_unit_bytes"] = number(unit);
    }
    read_only = boolean((volume.f_flag & ST_RDONLY) != 0);
  } else capacity.object["native_error"] = text(std::to_string(errno));
  errno = 0;
  long limit = fpathconf(root.fd,_PC_NAME_MAX); int limit_error = errno;
  names.object = {{"max_component_bytes",limit >= 0 ? number(u64(limit)) : Value{}},
    {"limit_kind",text(limit >= 0 ? "bounded" : limit_error ? "unknown" : "unbounded")},
    {"native_error",limit_error ? text(std::to_string(limit_error)) : Value{}},
    {"case_sensitive",{}},{"unicode_normalization",{}},{"invalid_utf8_supported",{}},
    {"forbidden_bytes_hex",text("002f")},{"dot_components_allowed",boolean(false)}};
  metadata.object = {{"permissions",{}},{"root_times",{}},{"extended_attributes",{}},{"acls",{}},{"file_flags",{}}};
#ifdef __APPLE__
  struct statfs fs{};
  if (!fstatfs(root.fd,&fs)) {
    type = text(fs.f_fstypename);
    if (!strcmp(fs.f_fstypename,"apfs") || !strcmp(fs.f_fstypename,"hfs")) names.object["unicode_normalization"] = boolean(true);
  }
  attrlist attributes{}; attributes.bitmapcount = ATTR_BIT_MAP_COUNT; attributes.volattr = ATTR_VOL_CAPABILITIES;
  struct { u32 length; vol_capabilities_attr_t caps; } capabilities{};
  if (!fgetattrlist(root.fd,&attributes,&capabilities,sizeof capabilities,0)) {
    auto bit = [&](unsigned group,u32 mask,bool invert = false) -> Value {
      return capabilities.caps.valid[group] & mask ? boolean(bool(capabilities.caps.capabilities[group] & mask) != invert) : Value{};
    };
    names.object["case_sensitive"] = bit(VOL_CAPABILITIES_FORMAT,VOL_CAP_FMT_CASE_SENSITIVE);
    metadata.object["permissions"] = bit(VOL_CAPABILITIES_FORMAT,VOL_CAP_FMT_NO_PERMISSIONS,true);
    metadata.object["root_times"] = bit(VOL_CAPABILITIES_FORMAT,VOL_CAP_FMT_NO_ROOT_TIMES,true);
    metadata.object["extended_attributes"] = bit(VOL_CAPABILITIES_INTERFACES,VOL_CAP_INT_EXTENDED_ATTR);
    metadata.object["acls"] = bit(VOL_CAPABILITIES_INTERFACES,VOL_CAP_INT_EXTENDED_SECURITY);
  }
#else
  struct statfs fs{};
  if (!fstatfs(root.fd,&fs)) {
    type = number(u64(fs.f_type));
    unsigned flags = 0; bool have_flags = ioctl(root.fd,FS_IOC_GETFLAGS,&flags) == 0;
    if (have_flags && (flags & FS_CASEFOLD_FL)) {
      names.object["case_sensitive"] = boolean(false); names.object["unicode_normalization"] = boolean(true);
    } else if (have_flags && fs.f_type == 0xef53) names.object["case_sensitive"] = boolean(true);
    if (fs.f_type == 0x4d44 || fs.f_type == 0x2011BAB0) names.object["case_sensitive"] = boolean(false);
  }
#endif
  if (faccessat(root.fd,".",W_OK|X_OK,AT_EACCESS) == 0) access = boolean(true);
  else if (errno == EACCES || errno == EPERM || errno == EROFS) access = boolean(false);
  if (read_only.kind == Value::Bool && read_only.boolean()) access = boolean(false);
  Value budget;
  if (space.kind != Value::Null) {
    std::vector<u64> sizes; u64 total = 0, rounded = 0; bool rounded_known = capacity.at("allocation_unit_bytes").kind == Value::String;
    u64 unit = rounded_known ? decimal(capacity.at("allocation_unit_bytes")) : 0;
    for (const auto& value : space.at("regular_file_sizes").array) {
      u64 size = decimal(value,INT64_MAX); total = add(total,size); sizes.push_back(size);
      if (rounded_known) {
        u64 remainder = size % unit, extra = remainder ? unit-remainder : 0;
        if (extra > UINT64_MAX-size || size+extra > UINT64_MAX-rounded) rounded_known = false;
        else rounded += size+extra;
      }
    }
    std::sort(sizes.begin(),sizes.end(),std::greater<u64>());
    u64 jobs = space.object.count("jobs") ? decimal(space.at("jobs"),64) : 64, staging = 0;
    for (size_t i = 0; i < std::min<size_t>(jobs,sizes.size()); ++i) staging = add(staging,sizes[i]);
    u64 retained = space.object.count("retained_logical_bytes") ? decimal(space.at("retained_logical_bytes")) : 0;
    budget = object();
    budget.object = {{"inputs_verified",boolean(false)},{"regular_files",number(sizes.size())},{"jobs_bound",number(jobs)},
      {"copy_logical_bytes",number(total)},{"atomic_staging_peak_logical_bytes",number(staging)},
      {"retained_logical_bytes",number(retained)},{"coexisting_data_logical_bytes",number(add(total,retained))},
      {"new_regular_data_allocation_estimate_bytes",rounded_known ? number(rounded) : Value{}},
      {"physical_requirement_bytes",{}},{"metadata_overhead_bytes",{}},{"quota_remaining_bytes",{}},
      {"data_budget_fits_available",rounded_known && capacity.at("available_bytes").kind == Value::String ? boolean(rounded <= decimal(capacity.at("available_bytes"))) : Value{}},
      {"retained_already_consumes_available",boolean(true)},{"reclaim_before_publication",boolean(false)},
      {"copy_uses_clone",boolean(false)},{"copy_uses_sparse",boolean(false)},{"filesystem_allocation_uncertainty",boolean(true)}};
  }
  if (fstat(root.fd,&after) || lstat(path.c_str(),&named)) fail(errno);
  auto current = DestinationRevision::from(after);
  if (!original.same_object(current) || !current.same_object(DestinationRevision::from(named))) fail(ESTALE);
  result.object = {{"type",text("destination_preflight")},{"endpoint",text("local")},{"path",app_json::parse(app_json::path(path))},
    {"revision",revision(current)},{"filesystem_type",type},{"read_only",read_only},{"directory_access_allowed",access},
    {"capacity",capacity},{"names",names},{"metadata",metadata},{"space",budget},{"advisory",boolean(true)},
    {"copy_authorized",boolean(false)},{"write_probe_performed",boolean(false)}};
  return result;
}
}
