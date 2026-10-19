# Este archivo contiene las instrucciones para compilar nuestros programas

#CXX --> Define el compilador LLVM Clang.
CXX := /opt/homebrew/opt/llvm/bin/clang++

#-std=c++17	--> Utiliza el estándar C++17
#-O3	--> Habilita optimizaciones del compilador.
# -Wall -Wextra -Wpedantic	--> Activa advertencias para detectar problemas.
# -ffp-contract=off	--> Desactiva la contracción de expresiones de punto flotante. Ayuda a mantener la precisión en cálculos numéricos.
# -fopenmp	--> Habilita el soporte para OpenMP, una API para programación paralela en C++.
CXXFLAGS := -std=c++17 -O3 -Wall -Wextra -Wpedantic -ffp-contract=off

# .PHONY --> indica que all es un objetivo simbólico, no un archivo que queremos generar. (indicamos que all debe ejecutar sus dependencias cuando lo solicitemos.)
.PHONY: all

# all --> Es el objetivo principal que compila todos los programas. Depende de bin/serial, bin/paralelo1 y bin/paralelo2.
all: bin/serial bin/paralelo1 bin/paralelo2

# Esta regla crea la carpeta donde guardaremos los programas compilados. (-p: no generar un error si el directorio ya existe.)
bin:
	mkdir -p bin
# Esta regla compila el programa serial. Depende del archivo fuente src/serial.cpp y del archivo de cabecera src/dbscan_common.hpp. El símbolo "|" indica que bin es una dependencia de orden, es decir, se debe crear antes de compilar el programa.
# $(CXX)	Compilador de C++
# $(CXXFLAGS)	Flags de compilación definidos anteriormente. (opciones de compilación)
# $<	Primera dependencia, en este caso src/serial.cpp
# -o	Indica el nombre del archivo de salida
# $@	Nombre del archivo de salida, en este caso bin/serial
bin/serial: src/serial.cpp src/dbscan_common.hpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@
# Esta regla compila el programa paralelo1. Depende del archivo fuente src/paralelo1.cpp y del archivo de cabecera src/dbscan_common.hpp. El símbolo "|" indica que bin es una dependencia de orden, es decir, se debe crear antes de compilar el programa.
# El símbolo % funciona como un comodín. --> Permite utilizar una sola regla para compilar diferentes versiones paralelas.
# $(CXX)	Compilador de C++
# $(CXXFLAGS)	Flags de compilación definidos anteriormente. (opciones de compilación)
# -fopenmp	--> Habilita el soporte para OpenMP
# $<	Primera dependencia, en este caso src/paralelo1.cpp
# -o	Indica el nombre del archivo de salida
# $@	Nombre del archivo de salida, en este caso bin/paralelo1
bin/paralelo%: src/paralelo%.cpp src/dbscan_common.hpp | bin
	$(CXX) $(CXXFLAGS) -fopenmp $< -o $@
