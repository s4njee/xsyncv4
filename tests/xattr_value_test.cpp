// Metadata workers must also run on musl's small default thread stack.
#include "xattr_value.h"
#include <pthread.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

namespace {
void* exercise(void*) {
  try {
    XattrValue small("same"), same("same"), different("other");
    if (!(small == same) || small == different) return (void*)1;
    XattrValue small_stored;
    if (!XattrValue::allocate(4, small_stored) || !small_stored.write("same", 4, 0) ||
        !(small_stored == small) || !(small == small_stored)) return (void*)1;
    std::string bytes(1 << 20, 'x');
    XattrValue stored(bytes), copy(bytes);
    if (!stored.stored() || !(stored == copy)) return (void*)1;
    bytes.back() = 'y';
    XattrValue changed(bytes);
    if (stored == changed) return (void*)1;
    std::string output;
    if (!changed.append_to(output) || output != bytes) return (void*)1;
    XattrValue allocated;
    if (!XattrValue::allocate(bytes.size(), allocated) ||
        !allocated.write(bytes.data(), bytes.size(), 0) || !(allocated == changed)) return (void*)1;
    FILE* file = tmpfile();
    if (!file) return (void*)1;
    bool written = fwrite(bytes.data(), 1, bytes.size(), file) == bytes.size() && fflush(file) == 0;
    XattrValue loaded;
    bool read = written && XattrValue::from_fd(fileno(file), bytes.size(), loaded);
    fclose(file);
    if (!read || !(loaded == changed)) return (void*)1;
    return nullptr;
  } catch (...) { return (void*)1; }
}
}

int main() {
  pthread_attr_t attrs;
  int error = pthread_attr_init(&attrs);
  if (error) { fprintf(stderr, "pthread attributes: %s\n", strerror(error)); return 1; }
  if (!error) error = pthread_attr_setstacksize(&attrs, 64 * 1024);
  pthread_t thread;
  if (!error) error = pthread_create(&thread, &attrs, exercise, nullptr);
  pthread_attr_destroy(&attrs);
  void* result = (void*)1;
  if (!error) error = pthread_join(thread, &result);
  if (error || result) {
    fprintf(stderr, "small-stack xattr regression failed: %s\n", error ? strerror(error) : "value mismatch");
    return 1;
  }
  puts("small-stack xattr comparison, allocation and streaming passed");
}
