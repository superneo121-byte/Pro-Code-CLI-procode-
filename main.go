package main

import (
	"github.com/superneo121-byte/Pro-Code-CLI-procode-/cmd"
	"github.com/superneo121-byte/Pro-Code-CLI-procode-/internal/logging"
)

func main() {
	defer logging.RecoverPanic("main", func() {
		logging.ErrorPersist("Application terminated due to unhandled panic")
	})

	cmd.Execute()
}
