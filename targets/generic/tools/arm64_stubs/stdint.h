
#ifndef _STDINT_H
#define _STDINT_H
typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long      uint64_t;
typedef unsigned long      uintptr_t;
typedef unsigned long      size_t;
#define UINT64_MAX (18446744073709551615UL)
#define PRIx64 "lx"
#define PRId64 "ld"
#define PRIu64 "lu"
#endif
