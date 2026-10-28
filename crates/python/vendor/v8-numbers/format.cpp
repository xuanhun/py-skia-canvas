// Original V8 DoubleToCString/IntToCString formatting, runtime-only helpers separated.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cassert>
#include "src/base/numbers/dtoa.h"
#define FPCLASSIFY_NAMESPACE std
namespace v8 { namespace internal {
bool IsInt32Double(double v) { return v>=INT32_MIN && v<=INT32_MAX && std::trunc(v)==v; }
int FastD2I(double v) { return static_cast<int>(v); }
class SimpleStringBuilder {
 char* data;int capacity;int index=0;
 public:SimpleStringBuilder(char* p,int n):data(p),capacity(n){}
 void AddCharacter(char c){assert(index+1<capacity);data[index++]=c;}
 void AddSubstring(const char* s,int n){for(int i=0;i<n;++i)AddCharacter(s[i]);}
 void AddString(const char* s){AddSubstring(s,static_cast<int>(std::strlen(s)));}
 void AddPadding(char c,int n){while(n-->0)AddCharacter(c);}
 void AddDecimalInteger(int n){char digits[16];int i=0;do{digits[i++]='0'+n%10;n/=10;}while(n);while(i)AddCharacter(digits[--i]);}
 const char* Finalize(){data[index]='\0';return data;}
};
const char* IntToCString(int n,base::Vector<char> buffer);
const char* DoubleToCString(double v, base::Vector<char> buffer) {
  switch (FPCLASSIFY_NAMESPACE::fpclassify(v)) {
    case FP_NAN:
      return "NaN";
    case FP_INFINITE:
      return (v < 0.0 ? "-Infinity" : "Infinity");
    case FP_ZERO:
      return "0";
    default: {
      if (IsInt32Double(v)) {
        // This will trigger if v is -0 and -0.0 is stringified to "0".
        // (see ES section 7.1.12.1 #sec-tostring-applied-to-the-number-type)
        return IntToCString(FastD2I(v), buffer);
      }
      SimpleStringBuilder builder(buffer.begin(), buffer.length());
      int decimal_point;
      int sign;
      const int kV8DtoaBufferCapacity = base::kBase10MaximalLength + 1;
      char decimal_rep[kV8DtoaBufferCapacity];
      int length;

      base::DoubleToAscii(
          v, base::DTOA_SHORTEST, 0,
          base::Vector<char>(decimal_rep, kV8DtoaBufferCapacity), &sign,
          &length, &decimal_point);

      if (sign) builder.AddCharacter('-');

      if (length <= decimal_point && decimal_point <= 21) {
        // ECMA-262 section 9.8.1 step 6.
        builder.AddString(decimal_rep);
        builder.AddPadding('0', decimal_point - length);

      } else if (0 < decimal_point && decimal_point <= 21) {
        // ECMA-262 section 9.8.1 step 7.
        builder.AddSubstring(decimal_rep, decimal_point);
        builder.AddCharacter('.');
        builder.AddString(decimal_rep + decimal_point);

      } else if (decimal_point <= 0 && decimal_point > -6) {
        // ECMA-262 section 9.8.1 step 8.
        builder.AddString("0.");
        builder.AddPadding('0', -decimal_point);
        builder.AddString(decimal_rep);

      } else {
        // ECMA-262 section 9.8.1 step 9 and 10 combined.
        builder.AddCharacter(decimal_rep[0]);
        if (length != 1) {
          builder.AddCharacter('.');
          builder.AddString(decimal_rep + 1);
        }
        builder.AddCharacter('e');
        builder.AddCharacter((decimal_point >= 0) ? '+' : '-');
        int exponent = decimal_point - 1;
        if (exponent < 0) exponent = -exponent;
        builder.AddDecimalInteger(exponent);
      }
      return builder.Finalize();
    }
  }
}

const char* IntToCString(int n, base::Vector<char> buffer) {
  bool negative = true;
  if (n >= 0) {
    n = -n;
    negative = false;
  }
  // Build the string backwards from the least significant digit.
  int i = buffer.length();
  buffer[--i] = '\0';
  do {
    // We ensured n <= 0, so the subtraction does the right addition.
    buffer[--i] = '0' - (n % 10);
    n /= 10;
  } while (n);
  if (negative) buffer[--i] = '-';
  return buffer.begin() + i;
}

} }
extern "C" void py_canvas_number_string(double value,char* output,int capacity){
 const char* text=v8::internal::DoubleToCString(value,v8::base::Vector<char>(output,capacity));
 if(text!=output){std::memmove(output,text,std::strlen(text)+1);}
}
