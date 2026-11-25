package main

import (
	"github.com/procode/procode/cmd"
	"github.com/procode/procode/internal/logging"
)

func main() {
	defer logging.RecoverPanic("main", func() {
		logging.ErrorPersist("Application terminated due to unhandled panic")
	})

	cmd.Execute()
}
