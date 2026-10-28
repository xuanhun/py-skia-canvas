#pragma once
#include <cstdint>
#include <cstring>
#define V8_BASE_EXPORT
#define V8_EXPORT_PRIVATE
#define V8_WARN_UNUSED_RESULT
#define V8_INLINE inline
#define V8_UNLIKELY(x) (x)
#define V8_LIKELY(x) (x)
namespace v8 { namespace base { template<class To,class From> inline To bit_cast(const From& from){static_assert(sizeof(To)==sizeof(From));To to;std::memcpy(&to,&from,sizeof(To));return to;} }}
