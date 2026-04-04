
#ifndef _STDLIB_H
#define _STDLIB_H
typedef unsigned long size_t;
#define NULL ((void*)0)
void *memset(void *s, int c, size_t n);
void *memcpy(void *dest, const void *src, size_t n);
void exit(int code) __attribute__((noreturn));
#endif
