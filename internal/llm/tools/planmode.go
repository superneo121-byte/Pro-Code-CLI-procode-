package tools

import "sync/atomic"

var planMode atomic.Bool

// SetPlanMode turns read-only "plan" mode on or off. While it is on, tools
// that change files or run commands refuse to run.
func SetPlanMode(on bool) { planMode.Store(on) }

// IsPlanMode reports whether plan mode is on.
func IsPlanMode() bool { return planMode.Load() }

// TogglePlanMode flips plan mode and returns the new state.
func TogglePlanMode() bool {
	for {
		old := planMode.Load()
		if planMode.CompareAndSwap(old, !old) {
			return !old
		}
	}
}

const planModeRefusal = "Plan mode is ON: this tool is disabled because it would change files or run commands. " +
	"Only read/search tools are available. Explain your plan to the user instead, and tell them to run the " +
	"\"Toggle Plan Mode\" command (Ctrl+K) to switch to build mode before making changes."
