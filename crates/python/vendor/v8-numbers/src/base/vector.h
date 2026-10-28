#pragma once
#include <cassert>
#include <algorithm>
#include "src/base/macros.h"
#include <cstring>
#include <cstdint>
#include "src/base/logging.h"
namespace v8 { namespace base {
template<class T>class Vector{T* p;int n;public:Vector():p(nullptr),n(0){} Vector(T* p,int n):p(p),n(n){} int length()const{return n;} T* data()const{return p;} T* begin()const{return p;} T* start()const{return p;} T* end()const{return p+n;} T& operator[](int i)const{assert(i>=0&&i<n);return p[i];} Vector<T> SubVector(int a,int b)const{return Vector<T>(p+a,b-a);} };
template<class T,int N>Vector<T> ArrayVector(T (&a)[N]){return Vector<T>(a,N);}
inline Vector<const char> CStrVector(const char* s){return Vector<const char>(s,static_cast<int>(std::strlen(s)));}
}}
