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
###

###
# For many of the tasks shown here we need a function extracting
# the numerical octets from a valid(!) IP string.
# => Returns a list with the four octets as integers.
#
def retrieve_octets(valid_octet_str: str) -> list[int]:
    octets = []
    for _ in range(3):
        octets.append(int(valid_octet_str[:valid_octet_str.index(".")]))
        valid_octet_str = valid_octet_str[valid_octet_str.index(".")+1:]

    octets.append(int(valid_octet_str))
    return octets


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
#   7)  The last octet must not be bigger than 252 ('11111100').¹
#
#   [1] In rare cases when using point-to-point connections, the
#       last octet may equal 254 ('11111110'); omitting both net-
#       work and broadcast addresses, only considering the ending
#       points' host addresses.
#       Because this is very rare, it won't be covered by this
#       function. Usually, such a mask would just
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


###
# Determining address classes and default subnet masks
# is important for clarification how many borrow bits
# actually are taken when subnetting a given network.
# How this is done?
# To make routing more efficient, once five basic address
# classes had been introduced:
#
#   +–{Class}–+–{1st byte's bits}–+–{Predefined bits}–+
#   |    A    |         1         |        0          |
#   +–––––––––+–––––––––––––––––––+–––––––––––––––––––+
#   |    B    |        1-2        |        10         |
#   +–––––––––+–––––––––––––––––––+–––––––––––––––––––+
#   |    C    |        1-3        |        110        |
#   +–––––––––+–––––––––––––––––––+–––––––––––––––––––+
#   |    D    |        1-4        |        1110       |
#   +–––––––––+–––––––––––––––––––+–––––––––––––––––––+
#   |    E    |        1-4        |        1111       |
#   +–––––––––+–––––––––––––––––––+–––––––––––––––––––+
#
# First bytes (octets) ranges and default subnet masks:
#
# Class A, range: 1-126; 127 reserved for loop-back;
#   Default subnet mask: 255.0.0.0; prefix /8;
#
# Class B, range: 128-191;
#   Default subnet mask: 255.255.0.0; prefix /16;
#
# Class C, range: 192-223;
#   Default subnet mask: 255.255.255.0; prefix /24;
#
# Class D, broadcast: 224-239;
# Class E, scientific purposes: 240-254.
#
# Therefore, we simply check the
# bit pattern of the first nibble (four bits) of the first
# octet from any given and valid(!) IPv4 address against
# the patterns from the table above.
# If it matches one out of these, we already got
# the address class.
# => The function returns class (i.e. "B"), subnet mask
# (i.e. "255.255.0.0") and prefix (i.e. "16").
#
def determine_addrclass(ip: str) -> list[str]:
    first_octet = retrieve_octets(ip)[0]
    if first_octet in range(1, 128):
        addrclass = "A"
        mask = "255.0.0.0"
        prefix = "8"
    elif first_octet in range(128, 192):
        addrclass = "B"
        mask = "255.255.0.0"
        prefix = "16"
    elif first_octet in range(192, 224):
        addrclass = "C"
        mask = "255.255.255.0"
        prefix = "24"
    elif first_octet in range(224, 240):
        addrclass = "D"
        mask = ""
        prefix = ""
    elif first_octet in range(240, 255):
        addrclass = "E"
        mask = ""
        prefix = ""

    return [addrclass, mask, prefix]


def main():
    ip = str(input(f"Enter IPv4 address: "))
    mask = str(input(f"Enter subnet mask: "))
    if is_ipaddr_valid(ip):
        print(f"\nIP address is valid:")
        print(f"\tAddress class: {determine_addrclass(ip)[0]}")
        print(f"\tDefault subnet mask: {determine_addrclass(ip)[1]}")
        print(f"\tDefault prefix: {determine_addrclass(ip)[2]}")
    else:
        print(f"\nIP address is invalid!")

    if is_subnetmask_valid(mask):
        print(f"\nSubnet mask is valid.")
    else:
        print(f"\nSubnet mask is invalid!")


if __name__ == "__main__":
    main()
