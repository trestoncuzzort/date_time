#define BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG
#include <boost/date_time/posix_time/posix_time.hpp>
#include <cstdint>
#include <iostream>

int main()
{
    using namespace boost::posix_time;
    const std::uint64_t scalar = 2793555578;
    const std::int64_t expected = 27935555780LL;
    const time_duration product = nanoseconds(10) * scalar;
    const time_duration quotient = nanoseconds(expected) / scalar;
    time_duration compound_product = nanoseconds(10);
    compound_product *= scalar;
    time_duration compound_quotient = nanoseconds(expected);
    compound_quotient /= scalar;
    std::cout << product.ticks() << ' ' << quotient.ticks() << ' '
              << compound_product.ticks() << ' ' << compound_quotient.ticks() << '\n';
    return (product.ticks() != expected) + (quotient.ticks() != 10)
         + (compound_product.ticks() != expected) + (compound_quotient.ticks() != 10);
}
