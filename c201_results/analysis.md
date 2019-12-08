Using fio, across the board for all reads/writes the internal emmc performs almost 2 times as well as the SD card and sometimes 3 to 4 times better. 
The most interesting fio test is the read/write random workloads. This mimics average usage by doing 90% reads and 10% writes randomly across the storage device.

The dd results are closer and inconclusive, with the sd card and emmc performing just about the same in each category.
Because dd does only sequential reads/writes, is single threaded, and is not designed for benchmarking storage devices like fio the dd results are flawed.
