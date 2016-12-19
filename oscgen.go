package main

import (
	"flag"
	"fmt"
	"math"
	"time"

	"github.com/hypebeast/go-osc/osc"
)

func main() {
	// Define variables to read from envocation line.
	// One can specify how many packets per second should be sent to OSC stream.
	var (
		argPort      uint
		argFrequency float64
	)

	flag.UintVar(&argPort, "port", 5000, "The port to which output the OSC stream.")
	flag.Float64Var(&argFrequency, "frequency", 500.0, "The frequency at which to send data (e.g. 500Hz).")

	flag.Parse()

	var (
		port   int           = int(argPort)
		period time.Duration = time.Duration(1 / argFrequency)
		phase  float64
	)

	client := osc.NewClient("127.0.0.1", port)
	start := time.Now()

	fmt.Printf("Generating output stream at %v Hz to port %v:\n", argFrequency, argPort)

	// Predefine array with values.
	var values [1000]float32
	for i := 0; i < 1000; i++ {
		phase += 2 * math.Pi / 1000
		value := float32(math.Sin(phase))
		values[i] = value
	}

	// Loop forever.
	for {
		// This loops resets the pointer i value to 0 each time it reaches the end of values array.
		for i := 0; i < 1000; i++ {
			elapsed := float64(time.Since(start)) / 1e9
			fmt.Printf("\rStreaming for %2.1fs", elapsed)

			msg := osc.NewMessage("/muse/eeg")
			value := values[i]
			// Differentiate between the arguemnts to output by adding an offset to each of them.
			msg.Append(value)
			msg.Append(value + 3)
			msg.Append(value + 6)
			msg.Append(value + 9)
			msg.Append(value + 12)
			msg.Append(value + 15)
			client.Send(msg)
			// Wait until it's time to send the next packet.
			time.Sleep(period * time.Microsecond)
		}
	}
}
