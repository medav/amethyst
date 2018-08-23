# Geode

Geode is an implementation of the classic 5-stage pipeline as described in Hennessy and Patterson's Computer Organization and Design (Risc-V Edition). It targets the RV64I ISA (and hopefully more in the future).

Geode is written in Atlas/Python. [Atlas](https://github.com/medav/atlas) is a Python-embedded-HDL similar to Chisel/Scala. Note that at the time of this project's creation, Atlas is still in the very early stages of development.

# Usage

## 1. Install Prerequisites
The following is required to use Geode:
* [Verilator](https://www.veripool.org/projects/verilator/wiki/Installing)
* [Python 3.7+](https://www.python.org)
* [Atlas](https://github.com/medav/atlas)
* (Optional) A waveform viewer (e.g. GtkWave)

## 2. Building the Simulator and Test App
To build the Verilator simulator and test application, simply run:

```
$ make
```

## 3. Run the Simulator
The compiled simulator is an executable application. Here is how to run it:

```
$ ./build/geode app/app.img
```

## 4. View the Output
The simulator produces a VCD dump as output. It can be opened with any waveform viewer.