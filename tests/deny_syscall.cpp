// Test-only seccomp launcher: exercise real kernel fallback and scan failures.
#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  int number = !strcmp(argv[1], "statx") ? SYS_statx :
               !strcmp(argv[1], "getdents64") ? SYS_getdents64 : -1;
  int error = atoi(argv[2]);
  if (number < 0 || error < 1 || error > 4095) return 2;
  sock_filter instructions[] = {
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(seccomp_data, nr)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (unsigned)number, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | (unsigned)error),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };
  sock_fprog filter{(unsigned short)(sizeof instructions / sizeof instructions[0]), instructions};
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) ||
      prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter)) {
    perror("install test seccomp filter"); return 2;
  }
  execvp(argv[3], argv + 3);
  perror("exec test binary"); return 2;
}
