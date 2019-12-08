#!/usr/bin/python3

#runs dd, fio to benchmark the read/write of the flash based boot device in different situations

# This file is part of PrawnOS (http://www.prawnos.com)
# Copyright (c) 2018 Hal Emmerich <hal@halemmerich.com>

# PrawnOS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation.

# PrawnOS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PrawnOS.  If not, see <https://www.gnu.org/licenses/>.

import subprocess
import os
import json

oneGiB=2**30
twoGiB=2*oneGiB
fourGiB=2*twoGiB
eightGiB=2*fourGiB
oneK=2**10
oneM=2**20

#returns the speed of the transfer in MB/s
def ddrun(ddcmd):
    out = subprocess.run(ddcmd.split(), stderr=subprocess.PIPE)
    outsplit = out.stderr.decode('utf-8').split()
    #convert GB to MB
    if outsplit[16] == "GB/s":
       return 1000 * float(outsplit[15])
    return float(outsplit[15])


def ddwrite(bs, count):
    ddcmd = "dd if=/dev/zero of=/tempfile bs={} count={} conv=fdatasync,notrunc".format(bs, count)
    return ddrun(ddcmd)


def ddread(bs, count):
    subprocess.run("echo 3 > /proc/sys/vm/drop_caches".split(), stdout=subprocess.PIPE)
    ddcmd = "dd if=/tempfile of=/dev/null bs={} count={}".format(bs, count)
    return ddrun(ddcmd)


def ddcacheread(bs, count):
    ddcmd = "dd if=/tempfile of=/dev/null bs={} count={}".format(bs, count)
    return ddrun(ddcmd)


def ddavg(bs, count):
    writetotal = 0
    readtotal = 0
    cachereadtotal = 0

    for i in range(4):
        writetotal = writetotal + ddwrite(bs, count)
        readtotal = readtotal + ddread(bs, count)
        cachereadtotal = cachereadtotal + ddcacheread(bs, count)
        os.remove("/tempfile")

    writeavg = writetotal / 4
    readavg = readtotal / 4
    cachereadavg = cachereadtotal / 4
    return writeavg, readavg, cachereadavg



def benchmarkdd(results):
    print("running dd benchmarks, this may take a while.....")
    filesizes = {"2GiB" : twoGiB, "4GiB" : fourGiB, "8GiB" : eightGiB}
    blocksizes = {"512" : 512, "4KiB" : (4*oneK), "16KiB" : (16*oneK), "64KiB": (64*oneK), "1MiB" : oneM, "50MiB" : (50*oneM)}
    results.write("### dd benchmarks ###\r\n")
    for fshuman, numbytes in filesizes.items():
        for bshuman, bsbytes in blocksizes.items():
            write, read, cacheread = ddavg(bshuman, (numbytes // bsbytes))
            print("################## dd {} bs={} avg results #######################".format(fshuman, bshuman))
            print("write = {}, read = {}, cached read = {}".format(write, read, cacheread))
            results.write("{}, {}, {}, {}, {}\r\n".format(write, read, cacheread, fshuman, bshuman))
    results.write("### dd benchmarks end ###\r\n")


def fiorun(bs, size, mode, rwmix=""):
    fiocmd = "fio --name=tempfile --rw={} --direct=1 --ioengine=libaio --bs={}  --size={} {} --output-format=json".format(mode, bs, size, rwmix)
    print(fiocmd)
    out = subprocess.run(fiocmd.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    # print( out.stdout.decode('utf-8'))
    outdict = json.loads(out.stdout.decode('utf-8'))
    if mode == "write" or mode == "randwrite":
        #get write bw
        writebwbytes = outdict["jobs"][0]["write"]["bw_bytes"]
        #return in MB/s since thats what dd provides
        return (float(writebwbytes) / 1000000)

    if mode == "read" or mode == "randread":
        #get read bw
        readbwbytes = outdict["jobs"][0]["read"]["bw_bytes"]
        #return in MB/s since thats what dd provides
        return (float(readbwbytes) / 1000000)

    if mode == "rw" or mode == "randrw":
        #get read/write bandwidth
        writebwbytes = outdict["jobs"][0]["write"]["bw_bytes"]
        readbwbytes = outdict["jobs"][0]["read"]["bw_bytes"]
        return (float(writebwbytes) / 1000000), (float(readbwbytes) / 1000000)

def fioavg(bs, size):
    writeseqtotal = 0
    readseqtotal = 0
    writerandtotal = 0
    readrandtotal = 0
    rw_readrandtotal = 0
    rw_writerandtotal = 0

    #run multiple times to remove noise
    repeat = 3
    for i in range(1, repeat):
        writeseqtotal = writeseqtotal + fiorun(bs, size, "write")
        readseqtotal = readseqtotal + fiorun(bs, size, "read")
        os.remove("tempfile.0.0")
        writerandtotal = writerandtotal + fiorun(bs, size, "randwrite")
        os.remove("tempfile.0.0")
        readrandtotal = readrandtotal + fiorun(bs, size, "randread")
        os.remove("tempfile.0.0")
        write, read = fiorun(bs, size, "randrw", "--rwmixread=90")
        rw_readrandtotal = rw_readrandtotal + read
        rw_writerandtotal = rw_writerandtotal + write
        os.remove("tempfile.0.0")

    writeseqavg = writeseqtotal / repeat
    readseqavg = readseqtotal / repeat
    writerandavg = writerandtotal / repeat
    readrandavg = readrandtotal / repeat
    rw_readrandavg = rw_readrandtotal / repeat
    rw_writerandavg = rw_writerandtotal / repeat

    return writeseqavg, readseqavg, writerandavg, readrandavg, rw_readrandavg, rw_writerandavg

def benchmarkfio(results):
    print("running fio benchmarks, this may take a while.....")
    filesizes = {"2GiB" : twoGiB, "4GiB" : fourGiB, "8GiB" : eightGiB}
    blocksizes = {"512", "4k", "16k", "64k", "1M", "50M"}
    results.write("### fio benchmarks ###\r\n")
    for fshuman, numbytes in filesizes.items():
        for bshuman in blocksizes:
            writeseqavg, readseqavg, writerandavg, readrandavg, rw_readrandavg, rw_writerandavg = fioavg(bshuman, fshuman)
            print("################## fio {} bs={} avg results #######################".format(fshuman, bshuman))
            print("write_seq = {}, read_seq = {}, write_rand = {}, read_rand = {}, rw_read_rand = {}, rw_write_rand".format(writeseqavg, readseqavg, writerandavg, readrandavg, rw_writerandavg, rw_readrandavg))
            results.write("{}, {}, {}, {}, {}, {}, {}, {}\r\n".format(writeseqavg, readseqavg, writerandavg, readrandavg, rw_writerandavg, rw_readrandavg, fshuman, bshuman))
    results.write("### fio benchmarks end ###\r\n")


#run everything
if os.geteuid() != 0:
   exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")
resultsfile = open("benchmarkResults.csv", "w+")
benchmarkfio(resultsfile)
benchmarkdd(resultsfile)
resultsfile.close()
