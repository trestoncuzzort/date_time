#include <boost/date_time/posix_time/posix_time_duration.hpp>
#include <boost/cstdint.hpp>
#include <iostream>
#include <string>

typedef boost::int64_t integer;
typedef boost::uint64_t word;
typedef boost::posix_time::time_duration duration;
word state = 0x31ef2ac452817defULL;
word digest = 1469598103934665603ULL;
word comparisons = 0, failures = 0, scenarios = 0;

word next()
{
  state ^= state << 13;
  state ^= state >> 7;
  state ^= state << 17;
  return state;
}

duration ticks(integer v) { return duration(0, 0, 0, v); }

void observe(const duration& actual, integer expected)
{
  ++comparisons;
  if (actual.is_special() || actual.ticks() != expected) ++failures;
  digest ^= static_cast<word>(actual.ticks());
  digest *= 1099511628211ULL;
}

template<class Integer>
void scenario(integer base, integer numerator, Integer factor)
{
  ++scenarios;
  const integer f = static_cast<integer>(factor);
  const integer product = base * f;
  const integer quotient = numerator / f;
  const duration original = ticks(base), dividend = ticks(numerator);
  observe(original * factor, product);
  observe(original, base);
  duration v = original;
  observe(v *= factor, product);
  observe(v, product);
  observe(dividend / factor, quotient);
  observe(dividend, numerator);
  v = dividend;
  observe(v /= factor, quotient);
  observe(v, quotient);
}

int main(int argc, char** argv)
{
  const bool small = argc == 2 && std::string(argv[1]) == "small";
  for (unsigned i = 0; i < 20000; ++i)
  {
    const integer base = static_cast<integer>(next() % 2000001) - 1000000;
    integer numerator = static_cast<integer>(next() % 1000000000000000000ULL);
    if (i % 2) numerator = -numerator;
    if (small)
    {
      const int factor = static_cast<int>(next() % 2000001) + 1;
      scenario(base, numerator, factor);
      scenario(base, numerator, -factor);
    }
    else
    {
      // All finite results fit signed 64 bits. Avoid low-32-bit zero so
      // the original narrowing control can complete rather than divide by 0.
      integer factor = static_cast<integer>(next() % 1099511627776ULL) + 1;
      if (static_cast<boost::uint32_t>(factor) == 0) ++factor;
      scenario(base, numerator, factor);
      scenario(base, numerator, static_cast<word>(factor));
      scenario(base, numerator, -factor);
    }
  }
  std::cout << "{\"scenarios\":" << scenarios << ",\"comparisons\":" << comparisons
            << ",\"failures\":" << failures << ",\"digest\":" << digest << "}\n";
  return failures ? 1 : 0;
}
