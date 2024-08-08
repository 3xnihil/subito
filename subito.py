#!/usr/bin/python
#
# SUBITO Subnetting utility - subito/subito.py
#
# Author: Johannes Hüffer
# Date: 08.08.2024 (beginning)
#
# This little program aims to support network technicians
# in creating networks and planning subnets.
#
# It aims to the following purposes in special:
#   1)  Putting out address ranges, subnet mask / prefix
#       on a given network. By default, the standard
#       address class is taken, but the user can choose
#       a different default subnet mask instead.
#   2)  If a certain amount of hosts is given, calculate
#       an appropriate subnet mask / prefix.
#       => Returns how many hosts and subnets the resulting
#       network would be capable of.
#       Optionally, a percentage can be provided in order
#       to calculate an address space reserve considering
#       future network growth.
#   3)  If a certain amount of subnets is given, calculate
#       an appropriate subnet mask / prefix.
#       => Returns how many subnets and hosts the resulting
#       network would be capable of.
#       Here, a percentage value considering future network
#       growth can also be taken into account.
#   4)  Offering simple tools being part of the above features like:
#           a) Determining the validity of an IPv4 address;
#           b) Determining the validity of a subnet mask;
#           c) Converting a subnet mask to a prefix and vice versa;
#           d) Determining the class of an IPv4 address and to which
#               use cases it is applicable.
#

###
# An IPv4 address is valid iff it fulfills the following conditions:
#   1)  It contains exactly three dots;
#   2)  It consists only of four numbers separated by these dots;
#   3)  Each number is in range between 0 and 255;
#   4)  The first octet must not begin with zero or 255.
#
def is_ipaddr_valid(ip: str) -> bool:
    dots_found = ip.count(".")
    octets = []
    valid_octets_found = 0

    if dots_found != 3:     # 1)
        return False

    else:
        # Extracting the first three octets
        for _ in range(3):
            octets.append(ip[:ip.index(".")])
            ip = ip[ip.index(".")+1:]

        # Remaining 'ip' string contains last octet (if so)
        octets.append(ip)
        
        for (n, octet) in enumerate(octets):
            if octet.isdigit():
                if n == 0 and int(octet) in range(1, 255):
                    valid_octets_found += 1
                elif n > 0 and int(octet) in range(0, 256):
                    valid_octets_found += 1
            else:
                return False

        return valid_octets_found == 4

        
def main():
    if is_ipaddr_valid("255.168.0.1"):
        print("IP is valid")
    else:
        print("IP is invalid")


if __name__ == "__main__":
    main()
