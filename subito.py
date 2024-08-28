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
# /!\ CRUCIAL: After adding the binary integers, we MUST make sure that the
#   resulting binary string is actually 32 characters long!
#   Reason: If the binary IP string contains leading zeros, int() will
#   stupidly cut them, resulting in an unvoluntary bit shift by the count
#   of bits which have been cut by int() before!
#   => Getting rid of this uninteded behaviour, I added the 'str.rjust()'
#   string operation to make sure we refill any missing leading zeros.
#
def calculate_subnet(net_addr: str, custom_prefix: int) -> list[str]:
    host_blocksize = 32 - custom_prefix
    total_hosts_per_block = 2 ** host_blocksize
    max_hosts_per_block = 2 ** host_blocksize - 2
    bin_net_addr = convert_octetstr_to_32_bitstr(net_addr)

    # Address of the next (succeeding) subnet
    bin_succeeding_subnet_addr = bin(
        int(bin_net_addr, 2) + total_hosts_per_block)[2:].rjust(32, "0")

    # Get the first host address of the current subnet
    bin_first_host_addr = bin(int(bin_net_addr, 2) + 1)[2:].rjust(32, "0")

    # Get the last host address of the current subnet
    bin_last_host_addr = bin(
        int(bin_net_addr, 2) + max_hosts_per_block)[2:].rjust(32, "0")

    # Now, determine current net's broadcast address
    bin_broadcast_addr = bin(
        int(bin_net_addr, 2) + max_hosts_per_block + 1)[2:].rjust(32, "0")

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
# The input list 'subnetting_userdata' is
# delivered by the 'input_config()' function
# and contains:
#  1. The original networks IP address;
#  2. A list of the total hosts, which's length
#     represents the amount of subnets.
#
# From the host counts, any necessary prefix can
# be calculated; enabling us to say how long a
# host address block has to become.
#
# => The function returns a list, containing all subnets'
# information lists (see 'calculate_subnet()')
# put into a single, super-ordinated list;
# ordered beginning from the largest network
# down to the smallest.
#
# TESTED: OK
#
def create_subnetting_list(subnetting_userdata: list) -> list[list]:
    orig_net_addr = subnetting_userdata[0]
    host_amounts = subnetting_userdata[1]
    prefixes = [calculate_prefix(host_amnt) for host_amnt in host_amounts]
    prefixes.sort()

    # Initial starting point: the original network address
    subnet_configs = [calculate_subnet(orig_net_addr, prefixes[0])]

    # Caution: A list comprehension will not work here,
    # because it deletes the initial network starting point
    # from the line above!
    for i in range(1, len(prefixes)):
        subnet_configs.append(calculate_subnet(
            subnet_configs[i-1][-1], prefixes[i]))

    return subnet_configs


###
# Extracting the data from the user's input config string.
# This string is of the form "#:#(#)", where "#" stands for
# any integer and round brackets may be omitted (if omitted,
# it just says we have only one network of this configuration).
# The first place before ":" denotes the currently demanded
# amount of hosts, while the place after ":" implies how big
# the reserve in percent should be (and therefore, on how many
# total hosts should be taken care of, since the host-blocksize of
# the subnet is to be oriented at the total size).
#
# => Via regular expression (regex) we can easily extract all
# valid patterns for host configs. Invalid ones will be ignored
# silently (the user most probably will detect any errors on the
# summary presented later on).
#
# ==> The function returns a list containing all resulting total
# host counts. Its length corresponds to the amount of subnets.
#
# IMPORTANT: A user must consider her-/himself whether to include
#   network and broadcast address into their calculations!
#   If a reserve percentage is provided, this may not bother, but
#   if no reserve (i.e. "120:0") is desired, definitely it should
#   be something to take care of!
#
# TESTED: OK
#
def retrieve_hosts_per_network(user_config_str: str) -> list[int]:
    from math import ceil
    import re

    regex_single_configs = re.compile(r'[0-9]+\:[0-9]+')
    regex_multi_configs = re.compile(r'[0-9]+\:[0-9]+\([0-9]+\)')

    single_configs = re.findall(regex_single_configs, user_config_str)
    multi_configs = re.findall(regex_multi_configs, user_config_str)

    total_hosts = []

    # The user config is taken seriously if at least two single-host ("#:#")
    # OR at least one multi-host config ("#:#(#)") could be found.
    # In this case, we can extract the data and calculate the desired
    # total host amounts:
    if len(single_configs) >= 2 or len(multi_configs) >= 1:
        for conf in single_configs:
            ondemand_hosts = int(conf[:conf.index(":")])
            reserve_percentage = int(conf[conf.index(":")+1:])
            total_hosts.append(
                ondemand_hosts + ceil(ondemand_hosts * (reserve_percentage/100)))

        for conf in multi_configs:
            ondemand_hosts = int(conf[:conf.index(":")])
            reserve_percentage = int(conf[conf.index(":")+1:conf.index("(")])
            x_times = int(conf[conf.index("(")+1:conf.index(")")])
            total = (ondemand_hosts +
                     ceil(ondemand_hosts * (reserve_percentage/100)))
            for _ in range(x_times-1):
                total_hosts.append(total)

        return total_hosts

    # Either no valid pattern found or config insufficient:
    else:
        return []


###
# ASKING DIALOG "YES/NO"
# Just a simple check-in if an option is desired or not.
#
def got_checked(prompt: str, is_yes_default: bool = False) -> bool:
    if is_yes_default:
        default_indicator = "[Y/n]"
    else:
        default_indicator = "[y/N]"

    choice = str(input(f"{prompt} {default_indicator}: "))

    # In case the user doesn't type and simply presses Enter (or any key)
    if not choice.isalpha() and is_yes_default:
        return True

    elif not choice.isalpha() and not is_yes_default:
        return False

    elif choice.isalpha() and choice[0].upper() == "Y":
        return True

    elif choice.isalpha() and choice[0].upper() == "N":
        return False

    # Invalid input should always deny the action in question
    else:
        return False


###
# Ask for subnet configuration contained in a string.
#
# TESTED: OK
#
def ask_hosts_per_subnets() -> list[int]:
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
                f"Each config block may\n"
                f"  be separated by colon from another.\n")

    example_question = (f"\nConfiguration:\n"
                        f"Enter desired "
                        f"host count AND "
                        f"reserve percentage PER EACH "
                        f"'on-demand' subnet.\n"
                        f"Give example?")

    if got_checked(example_question):
        print(hint_msg)

    hosts_per_subnets = str(input(f"Enter config string [#:#(#)]: "))
    hosts_per_subnets = retrieve_hosts_per_network(hosts_per_subnets)

    if len(hosts_per_subnets) == 0:
        print(f"You have to provide at least two subnet configs!\n"
              f" –> i.e. '160:40, 50:25' or '160:40(2)'")
        return ask_hosts_per_subnets()

    else:
        return hosts_per_subnets


###
# Very important is the verification of the user's desired
# configuration. It does not help anything if you have given
# a class C network to manage - you won't be able to get
# 10 subnets with 600 hosts, because with 4 borrow bits for
# the subnets already in use, only 4 host bits remain; delimiting
# your maximum host count per subnet up to 2⁴-2 = 14 hosts.
#
# Therefore, we need to calculate whether the provided net config
# will be possible. This has to be tested once per each subnet config
# of a certain type (i.e., if the user typed "1000:40, 400:20, 2:0(5)",
# we check if the blocksize fits for 1x subnet of 11 bits host blocksize
# and 1 subnetting bit, 1x subnet of 9 host bits and 1 subnetting bit
# and finally 5x subnets of 2 host bits and 3 subnetting bits).
#
# For each configuration:
#
# 1)    Check the on-demand amount of networks and calculate the
#       subnetting blocksize in bits.
# 2)    Add this subnetting blocksize to the default prefix of the
#       original network (i.e., if you have 192.168.10.0 and need
#       3 subnets, this would be as follows:
#           a) 192.x.x.x is a class C net with prefix /24;
#           b) 3 desired subnets result in two borrow bits required (your
#              subnetting bits);
#           c) so we calculate 24+2 = 26 bits for the network blocksize.
#           d) Therefore, we have 32-26 = 6 bits for the maximum
#              host blocksize;
#           e) resulting in 2⁶-2 = 62 hosts at max per subnet.
# 3)    Check the on-demand amount of hosts, for which we only have
#       to pick that of the largest demanded subnet, from which the
#       blocksize is calculated as well.
# 4)    Now, we subtract the default prefix from the entire 32-bit word,
#       giving us the totally available block size for the subnetting.
# 5)    If the subnetting is sufficient, subnet's blocksize
#       plus host's blocksize will fit the available total blocksize.
#
# TESTED: OK
#
def validate_user_subnets_blocksize_fit(user_net_host_config: list) -> list:
    orig_net_addr = user_net_host_config[0]
    orig_addrclass = determine_addrclass(orig_net_addr)[0]
    default_prefix = int(determine_addrclass(orig_net_addr)[2])

    hosts_per_subnets = user_net_host_config[1]
    hosts_per_subnets.sort()
    hosts_per_subnets = hosts_per_subnets[::-1]
    total_subnets_demanded = len(hosts_per_subnets)

    are_blocks_fitting = []
    faulty_subnets = ""

    for user_hosts_demanded in hosts_per_subnets:
        user_subnets_demanded = hosts_per_subnets.count(user_hosts_demanded)

        # When calculating the subnetting blocksize, we have to take
        # care of the fact that you can create two subnets with
        # 1 borrow bit, four with 2 borrow bits etc.
        # => This is due to permutations, because we always start
        # counting at zero.
        # I.e., if we need four subnets, 4 = 0b100, including 3 bits.
        # But we count from 0 to 3 in fact, such that 3 = 0b11
        # only requires 2 bits actually.
        # Therefore, we subtract 1 of the subnets which have been demanded.
        #
        # Speaking of the hosts, we don't have such a situation, since the
        # first available host number is always reserved for the network's address.
        #
        blocksize_user_hosts = len(bin(user_hosts_demanded)[2:])
        blocksize_user_subnets = len(bin(user_subnets_demanded - 1)[2:])

        total_blocksize_available = 32 - default_prefix
        total_blocksize_demanded = (
            blocksize_user_subnets + blocksize_user_hosts)

        are_blocks_fitting.append(
            total_blocksize_demanded <= total_blocksize_available)

    # Subnetting is only sufficient iff all subnet blocks fit their available blocksize
    if are_blocks_fitting.count(True) == total_subnets_demanded:
        return [True, ""]

    else:
        for (i, does_block_fit) in enumerate(are_blocks_fitting):
            if not does_block_fit:
                faulty_subnets += f"\t/!\ Subnet {i+1}:\t{hosts_per_subnets[i]} hosts\n"

        err_msg = (f"Sorry, some of your subnets exceed their maximum blocksize!\n"
                   f" –> Take a look at these subnets:\n"
                   f"{faulty_subnets}\n"
                   f" You have to figure out if you:\n"
                   f"   a) exceeded the maximum subnets for this prefix or\n"
                   f"   b) exceeded the maximum hosts, causing a collision "
                   f"with the subnetting block.\n\n"
                   f" These options might help you:\n"
                   f"   1) Reduce the amount of hosts in these subnets,\n"
                   f"   2) Reduce the amount of troublesome subnets themselves or\n"
                   f"   3) If possible, use an upper address class "
                   f"(> {orig_addrclass}) for your original network.\n")

        return [False, err_msg]


###
# Show the resulting subnets, ordered from the
# largest to the smallest networks:
#
# TESTED: OK
#
def print_final_subnets(subnetting_list: list[list], user_net_host_config: list) -> None:
    # Caution! The original list 'user_net_host_config' contains only two elements:
    # the IP address of the network and a list with the actual host counts!
    # Therefore, we have to extract that list first and arrange its items from
    # the largest down to the smallest:
    hosts_per_subnets = user_net_host_config[1]
    hosts_per_subnets.sort()
    hosts_per_subnets = hosts_per_subnets[::-1]
    total_subnets = len(subnetting_list)

    for (i, subnet) in enumerate(subnetting_list):
        max_hosts = 2 ** len(bin(hosts_per_subnets[i])[2:]) - 2
        print(f"Subnet ({i+1}):"
              f"\tNetwork address: {subnet[0]}"
              f"/{convert_subnetmask_to_prefix(subnet[1])} "
              f"({max_hosts} hosts)\n"
              f"\t\tSubnet mask:\t{subnet[1]}\n"
              f"\t\tFirst host:\t{subnet[2]}\n"
              f"\t\tLast host:\t{subnet[3]}\n"
              f"\t\tBroadcast:\t{subnet[4]}\n")


###
# WRITE SUBNETTING CONFIG TO A SPREADSHEET
# This function only performs the actual writing of the final
# subnet configs to an Excel file.
#
# TESTED: OK
#
def write_subnetting_conf_to_excelfile(
        filename: str, subnetting_list: list[list],
        user_net_host_config: list) -> None:

    import xlsxwriter

    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet(name="SUBito netplan")

    hosts_per_subnets = user_net_host_config[1]
    hosts_per_subnets.sort()
    hosts_per_subnets.reverse()
    total_subnets = len(subnetting_list)

    col_titles = ["Subnet no.", "Max. hosts",
                  "Network addr.", "Subnet mask",
                  "First host addr.", "Last host addr.",
                  "Broadcast addr."]

    # Fill in the titles of the columns, first
    for (col, title) in enumerate(col_titles):
        worksheet.write(0, col, title)

    # Now, we can write down all the networks' data
    for (i, subnet) in enumerate(subnetting_list):
        max_hosts = 2 ** len(bin(hosts_per_subnets[i])[2:]) - 2

        # The subnet's number
        worksheet.write(i + 1, 0, i + 1)

        # Maximum host amount for this subnet
        worksheet.write(i + 1, 1, max_hosts)

        # The subnet's own address
        worksheet.write(
            i + 1, 2, f"{subnet[0]}/{convert_subnetmask_to_prefix(subnet[1])}")

        # All other data: subnet mask, first host, last host and broadcast addresses
        for j in range(1, 5):
            worksheet.write(i + 1, j + 2, subnet[j])

    # Important: Finally close the file!
    workbook.close()
    print(f" –> Stored spreadsheet into your working dir.\n"
          f" Have a nice day :)\n")


###
# CREATING NETWORK SPREADSHEETS
# Maybe users not only like to get an overview about their new
# subnetting rather than create an entire network plan.
# Because this can become a tedious and time-consuming job, this
# function creates an Excel sheet template in order to make
# this task much easier.
#
# ==> This function checks first if the module "XlsxWriter" is installed.
# If not, the user is prompted to install it first and then to run this
# script again.
#
# If the module is installed, the function asks for a filename and then
# writes a valid(!) subnetting configuration into an Excel spreadsheet
# (which of course is readable by most other spreadsheet calculation apps).
#
# TESTED: OK
#
def save_subnetting_conf(
        filename: str, subnetting_list: list[list],
        user_net_host_config: list) -> None:

    try:
        write_subnetting_conf_to_excelfile(
            filename, subnetting_list, user_net_host_config)

    except ImportError:
        print(f"Creating spreadsheets requires Python module 'XlsxWriter'!\n"
              f" Please, install the missing module first.\n"
              f" –> It's recommended to use Python's package manager, pip:\n"
              f"  System-wide:\t\tpython -m pip install xlsxwriter\n"
              f"  Per user only:\tpython -m pip install --user xlsxwriter\n\n"
              f" After that, run SUBito again and you are ready ;)\n")

        if got_checked("If lazy, try unorthodox pip auto-install?"):
            from subprocess import run
            run(["python", "-m", "pip", "install", "--user", "xlsxwriter"])
            print(f"\nNegligently not knowing the exit status of the install,\n"
                  f"trying to create your Excel spreadsheet again ...\n")

            try:
                write_subnetting_conf_to_excelfile(
                    filename, subnetting_list, user_net_host_config)

            except ImportError:
                print(f"Well, did my best 0~0\n"
                      f" –> Seems like you have to install xlsxwriter module manually.\n")

        else:
            print(f"Wise decision ;)\n"
                  f"–> It's best to install Python modules by yourself.\n")


###
# CONFIGURATOR
# Asking all configuration options from the user.
#
# TESTED: OK
#
def input_config() -> list:
    orig_net_addr = ask_net_addr()
    hosts_per_subnets = ask_hosts_per_subnets()
    return [orig_net_addr, hosts_per_subnets]


def main():
    print(f"\n*** SUBito 0.2 – subnetting tool ***\n")
    user_subnet_config = input_config()
    subnetting_check = validate_user_subnets_blocksize_fit(user_subnet_config)

    if subnetting_check[0]:
        subnet_specs = create_subnetting_list(user_subnet_config)
        print_final_subnets(subnet_specs, user_subnet_config)

        if got_checked("Save this config?", True):
            save_subnetting_conf(
                "subito_subnetting.xlsx", subnet_specs, user_subnet_config)

        else:
            print(f" –> Nothing saved. See you :)\n")

    else:
        print(subnetting_check[1])


if __name__ == "__main__":
    main()
