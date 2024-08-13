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
# A usual exercise consists of creating a networking plan.
# This function aims to auto-solve subnetting even with
# the more complex VLSM method.
#
#   FLSM (Fixed Length Subnet Mask):
#       All subnets have the same size (address space).
#       Fairly easy to configure and maintain, but wasting IP addresses.
#
#   VLSM (Variable Length Subnet Mask):
#       Today's standard in IPv4 subnetting.
#       Subnets may have different block sizes, which is
#       commonly used in order to save address space and improve security.
#       In example, you don't need more than two host addresses for
#       point-to-point connections between routers. Hence, (aside from
#       network and broadcast addresses) only two host addresses are
#       required for such a net.
#
#   ==> This tool aims to make VLSM quite easy to configure.
#
# Starting from a given IP address (and subnet mask or prefix),
# a list of options has to be found out about:
#
#   1) The original network address.
#       It is important to determine the default address class
#       and prefix / subnet mask of the network such that we
#       can tell how many borrow bits (subnetting bits) will
#       be in use.
#         Further, subnetting will entirely be regretted
#       for class D and E networks (since they serve entirely
#       different purposes) as well as addresses starting with
#       127.x.x.x, because they are reserved for link-local.
#         However, any address will surely be checked for its
#       overall validity.
#
#   2) Telling the network's arragement.
#       This tool has to know exactly:
#           a) How many subnets are currently required ("on-demand"),
#               and which reserve in subnets it should
#               hold back (a percentage for future growth),
#           b) How many hosts PER EACH subnet are demanded and
#               whether future growth has to be considered (percentage).
#
# The program tells whether this configuration is possible (in terms of
# subnets vs. hosts and desired quantities) and, if it is, shows a
# network plan with all subnets and their address spaces.
#
# Put into a user-friedly CLI, this would be like:
#
#           *** SUBITO – subnetting tool ***
#
#           Original network's address [#.#.#.#]: 172.16.0.0
#             –> Class is B. Default prefix: /16
#
#           Configuration: Enter desired host count AND
#                reserve percentage PER EACH 'on-demand' subnet.
#               Give example? [y/N]: Y
#
#             –> You need 5 subnets in total. These are called your
#                on-demand subnets.
#                2 of them are point-to-point networks,
#                3 of them should contain 150 hosts with 20% reserve,
#                the remaining address space is in reserve.
#
#                For this choice, you would enter: 2:0(2),150:20(3)
#
#           Syntax: <hosts on-demand>:<reserve percent>(<'n' configs>)
#
#                The round brackets may be omitted if only one subnet of
#                this configuration is wished-for. Each config block has
#                to be separated by colon from another.
#
#           Enter config string [#:#(#)]: 2:0(2),150:20,7:35,30:50
#
#           Summary: Original network: 172.16.0.0/16
#                    5 total subnets:
#                       (1) 150 hosts, 20% reserve  (total: 254)
#                       (2)  30 hosts, 50% reserve  (total: 62)
#                       (3)   7 hosts, 35% reserve  (total: 14)
#                       (4)   2 hosts, PTP          (total: 2)
#                       (5)   2 hosts, PTP          (total: 2)
#
#           Subnet (1): Network addr: 172.16.0.0/24 (254 hosts)
#                       Subnet mask:  255.255.255.0
#                       First host:   172.16.0.1
#                       Last host:    172.16.0.254
#                       Broadcast:    172.16.0.255
#
#           Subnet (2): Network addr: 172.16.1.0/26 (62 hosts)
#                       Subnet mask:  255.255.255.192
#                       First host:   172.16.1.1
#                       Last host:    172.16.1.62
#                       Broadcast:    172.16.1.63
#
#           ~~~~~~~~~~~~~ Press Enter to show more ~~~~~~~~~~~~~
#
#
#   6)  Offering simple tools being part of the above features like:
#           a) Determining the validity of an IPv4 address;
#           b) Determining the validity of a subnet mask;
#           c) Converting a subnet mask to a prefix and vice versa;
#           d) Determining the class of an IPv4 address and to which
#               use cases it is applicable, etc ...


#####################################################################
#                                                                   #
# Internal functions without special error handling, expecting      #
# validated inputs (except for the validator functions of course ;) #
#                                                                   #
#####################################################################


###
# For many of the tasks shown here we need a function extracting
# the numerical octets from a valid(!) IP string.
# => Returns a list with the four octets as integers.
#
# TESTED: OK
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
# TESTED: OK
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
# TESTED: OK
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

        # Remaining 'ip' string contains last octet
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
# A prefix is valid iff it is in range between 1-30.¹
#
# [1] In rare cases the prefix may be extended up to 31,
#   when using point-to-point connections. This won't be
#   covered here, because we don't usually want this.
#
# TESTED: OK
#
def is_prefix_valid(prefix: str) -> bool:
    return prefix.isdigit() and int(prefix) in range(1, 31)


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
# TESTED: OK
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


###
# Convert subnet mask (regular octet string) to prefix.
# Only applicable to already validated mask-strings!
#
# TESTED: OK
#
def convert_subnetmask_to_prefix(mask: str) -> int:
    dec_octets = retrieve_octets(mask)
    return "".join([(bin(dec_octet)[2:]).rjust(8, "0")
                    for dec_octet in dec_octets]).count("1")


###
# Convert prefix to subnet mask (human-readable octets).
# Only applicable to validated prefixes!
#
# TESTED: OK
#
def convert_prefix_to_subnetmask(prefix: int) -> str:
    bin_prefix = ("1" * prefix).ljust(32, "0")
    bin_octets = [bin_prefix[n:n+8] for n in range(0, 25, 8)]
    return ".".join([str(int(bin_octet, 2)) for bin_octet in bin_octets])


###
# We have to know how long the prefix for a requested subnet
# ideally has to be.
# It is calculated by subtracting the binary block length of
# the maximum host amount from the entire block length of an
# IPv4 address, which equals 32.
#
# TESTED: OK
#
def calculate_prefix(n_hosts: int) -> int:
    binary_host_blocksize = len(bin(n_hosts)[2:])
    return 32 - binary_host_blocksize


###
# Converting a binary 32-char string (representing 32 bits)
# back to a string in human-readable decimal octet format
# with separation marks (dot notation).
#
# TESTED: OK
#
def convert_32_bitstr_to_octetstr(bin_str: str) -> str:
    bin_octets = [bin_str[n:n+8] for n in range(0, 25, 8)]
    dec_octets = [int(bin_octet, 2) for bin_octet in bin_octets]
    return ".".join([str(dec_octet) for dec_octet in dec_octets])


###
# Converting a human-readable octet string (of an IP address or
# subnet mask) to a binary 32-char string (representing 32 bits).
# The output binary string does not contain any separators and
# only '1's and '0's.
#
# TESTED: OK
#
def convert_octetstr_to_32_bitstr(octet_str: str) -> str:
    dec_octets = retrieve_octets(octet_str)
    bin_octets = [(bin(dec_octet)[2:]).rjust(8, "0")
                  for dec_octet in dec_octets]
    return "".join(bin_octets)


###
# Determines all relevant data points of any given network:
#   1)  Its own address of course,
#   2)  its own subnet mask,
#   3)  its first host address,
#   4)  its last host address,
#   5)  its broadcast address and finally
#   6)  the address of its successor network.
#
# All of these data point we can figure out easily.
# I.e. when creating subnets, we are able to determine the next subnet's
# address by just adding the entire subnet's blocksize (all host addresses
# including network and broadcast) to the previous subnet's address.
#
# Example: 172.16.0.0/24; class B net with original prefix /16 provides
#   2⁸ = 256 subnets. Each host address block therefore is 8 bits large,
#   resulting in 256 total addresses per block (with 254 usable hosts).
#
#   The next subnet address would be 172.16.1.0, because we have a
#   carry-bit when stepping from 255 (host broadcast) to 0 (next network):
#
#                       Mask: 255.255.1111 1111.0000 0000 (255.255.255.0)
#      Broadcast, 1st subnet: 172. 16.0000 0000.1111 1111 (172.16.0.255)
#       Net addr, 2nd subnet: 172. 16.0000 0001.0000 0000 (172.16.1.0)
#
# TESTED: OK
#
def calculate_subnet(net_addr: str, custom_prefix: int) -> list[str]:
    host_blocksize = 32 - custom_prefix
    total_hosts_per_block = 2 ** host_blocksize
    max_hosts_per_block = 2 ** host_blocksize - 2
    bin_net_addr = convert_octetstr_to_32_bitstr(net_addr)

    # Address of the next (succeeding) subnet
    bin_succeeding_subnet_addr = bin(
        int(bin_net_addr, 2) + total_hosts_per_block)[2:]

    # Get the first host address of the current subnet
    bin_first_host_addr = bin(int(bin_net_addr, 2) + 1)[2:]

    # Get the last host address of the current subnet
    bin_last_host_addr = bin(
        int(bin_net_addr, 2) + max_hosts_per_block)[2:]

    # Now, determine current net's broadcast address
    bin_broadcast_addr = bin(
        int(bin_net_addr, 2) + max_hosts_per_block + 1)[2:]

    # The binary 32-bit address strings have to be
    # retransformed into human-readable octet strings:
    succeeding_subnet_addr = convert_32_bitstr_to_octetstr(
        bin_succeeding_subnet_addr)
    first_host_addr = convert_32_bitstr_to_octetstr(bin_first_host_addr)
    last_host_addr = convert_32_bitstr_to_octetstr(bin_last_host_addr)
    broadcast_addr = convert_32_bitstr_to_octetstr(bin_broadcast_addr)

    # Finally, provide the subnet mask
    subnetmask = convert_prefix_to_subnetmask(custom_prefix)

    return [net_addr,
            subnetmask,
            first_host_addr,
            last_host_addr,
            broadcast_addr,
            succeeding_subnet_addr]


##########################################################################
#                                                                        #
# User functions with error handling for safe input ("Gorilla-proof") ;) #
#                                                                        #
##########################################################################

###
# Asking for the original network's IP address.
# If the user makes an input mistake, the function calls itself;
# hoping, no real gorilla sitting in front of the machine ^^
#
# TESTED: OK
#
def ask_net_addr() -> str:
    entered_addr = str(input(f"Original network's address [#.#.#.#]: "))

    if is_ipaddr_valid(entered_addr):
        addrclass = determine_addrclass(entered_addr)[0]
        default_prefix = determine_addrclass(entered_addr)[2]
        first_octet = int(retrieve_octets(entered_addr)[0])

        if addrclass in "ABC" and first_octet != 127:
            print(f"–> Class is {addrclass}. "
                  f"Default prefix: /{default_prefix}")
            return entered_addr

        else:
            print(f"–> Class D, E and link-local addresses "
                  f"(127.x.x.x) are forbidden!\n"
                  f"Suitable for subnetting are the classes\n"
                  f"\tA (1-126.x.x.x),\n"
                  f"\tB (128-191.x.x.x) and\n"
                  f"\tC (192-223.x.x.x).\n")
            return ask_net_addr()

    else:
        print(f"–> No valid IP address.\n Please, try again ...\n")
        return ask_net_addr()


###
# Core function, performs the actual subnetting.
# Before we can start, we have to bring the
# subnets in a suitable order, beginning with
# the shortest prefix (largest network) and
# finalizing with the longest (smallest network).
#
# The succeeding network always has the first address
# of the next free address block determined by
# the preceeding network.
#
# The input list 'host_amounts' is
# delivered by the 'input_config()' function
# and contains the final amount of hosts per
# network. From these, any necessary prefix can
# be calculated; enabling us to say how long a
# host address block has to become.
#
# => It returns a list, containing all subnets'
# information lists (see 'calculate_subnet()')
# put into a single, super-ordinated list;
# ordered beginning from the largest network
# down to the smallest.
#
# TESTED: OK
#
def create_subnetting_list(orig_net_addr: str, host_amounts: list[int]) -> list[list]:
    prefixes = [calculate_prefix(host_amnt) for host_amnt in host_amounts]
    prefixes.sort()

    # Initial starting point: the original network address
    subnet_configs = [calculate_subnet(orig_net_addr, prefixes[0])]

    # Caution: A list comprehension will not work here, because it deletes the initial
    # network starting point from the line above!
    for i in range(1, len(prefixes)):
        subnet_configs.append(calculate_subnet(
            subnet_configs[i-1][-1], prefixes[i]))

    return subnet_configs


###
# Ask for subnet configuration contained in a string.
#
# FIXME: Under construction!
#
def ask_subnets() -> list:
    hint_msg = (f"\n–> Suppose, you'd need 5 subnets in total.\n"
                f"These are called your on-demand subnets.\n"
                f"  2 of them are point-to-point networks,\n"
                f"  3 of them should contain 150 hosts with "
                f"20% reserve,\n"
                f"  the remaining address space is in reserve.\n\n"
                f"For this choice, you'd enter: 2:0(2),150:20(3)\n\n"
                f"Syntax: <hosts on-demand>:<reserve percent> "
                f"(<'n' configs>)\n\n"
                f"  The round brackets may be omitted if only "
                f"one subnet of\n"
                f"  this configuration is wished-for. "
                f"Each config block has\n"
                f"  to be separated by colon from another.\n")

    example_choice = str(input(f"\nConfiguration:\n"
                               f"Enter desired "
                               f"host count AND "
                               f"reserve percentage PER EACH "
                               f"'on-demand' subnet.\n"
                               f"Give example? [y/N]: "))

    if example_choice.isalnum() and example_choice[0].upper() == "Y":
        print(hint_msg)

    user_config = str(input(f"Enter config string [#:#(#)]: "))

    # FIXME: Filter string by a regex!

    return []


###
# Asking all configuration options from the user.
#
def input_config() -> list:
    orig_net_addr = ask_net_addr()
    chosen_subnet_configs = ask_subnets()
    return [orig_net_addr, chosen_subnet_configs]


def main():
    print(create_subnetting_list("172.16.0.0", [2, 2, 14, 62, 254]))
    # net_config = input_config()


if __name__ == "__main__":
    main()
