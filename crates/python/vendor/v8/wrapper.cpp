#include "src/base/ieee754.h"
extern "C" {
double py_canvas_dom_sin(double x) { return v8::base::ieee754::sin(x); }
double py_canvas_dom_cos(double x) { return v8::base::ieee754::cos(x); }
double py_canvas_dom_tan(double x) { return v8::base::ieee754::tan(x); }
double py_canvas_dom_atan2(double y,double x) { return v8::base::ieee754::atan2(y,x); }
}
