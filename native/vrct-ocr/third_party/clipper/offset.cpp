// What pyclipper 1.4.0 does for RapidOCR's unclip:
//   PyclipperOffset(miter_limit=2.0, arc_tolerance=0.25).AddPath(box, JT_ROUND, ET_CLOSEDPOLYGON)
//   Execute(delta) -> Paths
// clipper.cpp / clipper.hpp are the Clipper 6.4.2 sources shipped in the pyclipper 1.4.0 sdist
// (Boost Software License 1.0, see LICENSE_1_0.txt).
#include <cstdlib>
#include <cstring>

#include "clipper.hpp"

using namespace ClipperLib;

extern "C" {

// xy: n points as x0, y0, x1, y1, ... The result is every output path's points concatenated
// (RapidOCR reshapes the result to (-1, 1, 2)); free it with vrct_clipper_free.
long long* vrct_clipper_offset_round(const long long* xy, size_t n, double delta, size_t* out_points) {
  Path path;
  for (size_t i = 0; i < n; ++i)
    path.push_back(IntPoint(xy[2 * i], xy[2 * i + 1]));
  ClipperOffset offset(2.0, 0.25);
  offset.AddPath(path, jtRound, etClosedPolygon);
  Paths solution;
  offset.Execute(solution, delta);
  size_t total = 0;
  for (const Path& p : solution)
    total += p.size();
  long long* out = static_cast<long long*>(std::malloc((total ? total : 1) * 2 * sizeof(long long)));
  size_t k = 0;
  for (const Path& p : solution)
    for (const IntPoint& pt : p) {
      out[k++] = pt.X;
      out[k++] = pt.Y;
    }
  *out_points = total;
  return out;
}

void vrct_clipper_free(long long* p) { std::free(p); }

}
