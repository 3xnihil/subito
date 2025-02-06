# SUBito
*lat. "subito" = immediately*
## Python-based IPv4 subnetting utility
If you have middle up to large-scale networks to configure, this could be a tool for you.
You only have to provide a network address, and *SUBito* will calculate all the subnets for you.
At the end, you may even decide whether to save the config to an Excel file, making a great starting point for further
improvements.
### Requirements
* Python, of course (version 3)
* Python module *xlsxwriter* [1]
* *Optional but useful*: Knowing how to set up a Python virtual environment
---
[1] At time of writing I added this in a hurry. Future versions might come aptly packaged with all the dependencies
as one could expect ;)
### Setup (any *nix-based OS)
1. It's recommended to create a venv first:
`python3 -m venv subito`
2. Switch to the venv: `source subito/bin/activate`
3. Install *xlsxwriter* via pip: `pip install xlsxwriter`
4. Leave the venv: `deactivate`
### Usage
* On startup, you'll be asked for a network address
* You will be asked for a network *config string*
* The *config string*: `<hosts on-demand>:<reserve percent> (<'n' configs>)`
* `<hosts on-demand>`: How many hosts/clients/interfaces should connect to?
* `<reserve percent>`: Buffer for future expansion in percent (zero for none)
* `(<'n' configs>)`: *Optional*. Duplicate this subnet block *n* times (saves a lot of time)
* You can put several *config strings* in a row: `<config string 1>, <config string 2>, ...`
* Example: `2:0(10), 300:20(2), 40:40, 10:20(4)`
* This would create 10 point-to-point nets (zero buffer), 2 nets for 300 hosts serving 20% buffer, single net for 40 hosts serving 40% buffer etc.