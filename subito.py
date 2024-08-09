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
# A subnet mask is valid iff it fulfills the following criteria:
#   1)  It contains exactly three dots;
#   2)  It consists of four numbers separated by these dots;
#   3)  Each number (octet) is in range between 0 and 255;
#   4)  The octet matches an 8-bit value representing a straight
#       row of '1'-bits going from left to right (i.e. '11111100'
#       or '10000000', but not '00100001' etc.);
#   5)  If the predecessor of an octet ends with a zero, all(!)
#       of its succeeding octets must equal zero;
#   6)  The first octet must not equal zero;
#   7)  The last octet must not be bigger than 252¹ ('11111100').
#
#   [1] In rare cases when using point-to-point connections, the
#       last octet may equal 254 ('11111110'); omitting both net-
#       work and broadcast addresses, only considering the ending
#       points host addresses.
#       Because this is very rare, it won't be covered by this
#       function. In most cases such a mask would just
#       be insufficient or not be accepted.
#
def is_subnetmask_valid(mask: str) -> bool:
    dots_found = mask.count(".")
    octets = []
    valid_octets = [0, 128, 192, 224, 240, 248, 252, 254, 255]
    valid_octets_found = 0

    if dots_found == 3:
        for _ in range(3):
            octets.append(mask[:mask.index(".")])
            mask = mask[mask.index(".")+1:]

        octets.append(mask)

        for (n, octet) in enumerate(octets):
            if octet.isdigit():
                octet = int(octet)
                if n == 0 and octet != 0 and octet in valid_octets:
                    valid_octets_found += 1
                elif (n > 0 and octet != 0 and octet in valid_octets and
                      int(octets[n-1]) == 255):
                    valid_octets_found += 1
                elif (n > 0 and octet == 0 and
                      int(octets[n-1]) in valid_octets):
                    valid_octets_found += 1

            else:
                return False

        return valid_octets_found == 4

    else:
        return False


###
# An IPv4 address is valid iff it fulfills the following conditions:
#   1)  It contains exactly three dots;
#   2)  It consists of four numbers separated by these dots;
#   3)  Each number is in range between 0 and 255;
#   4)  The first octet must not begin with zero or 255.
#
def is_ipaddr_valid(ip: str) -> bool:
    dots_found = ip.count(".")
    octets = []
    valid_octets_found = 0

    if dots_found == 3:
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

    else:
        return False


def main():
    if is_ipaddr_valid("124.10.0.1"):
        print("IP is valid")
    else:
        print("IP is invalid")

    if is_subnetmask_valid("255.255.128.0"):
        print("Mask is valid")
    else:
        print("Mask is invalid")


if __name__ == "__main__":
    main()
