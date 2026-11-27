package tools

import (
	"context"
	"testing"
)

func TestPlanModeToggle(t *testing.T) {
	SetPlanMode(false)
	defer SetPlanMode(false)

	if IsPlanMode() {
		t.Fatal("plan mode should start off")
	}
	if !TogglePlanMode() || !IsPlanMode() {
		t.Fatal("toggle should turn plan mode on")
	}
	if TogglePlanMode() || IsPlanMode() {
		t.Fatal("second toggle should turn plan mode off")
	}
}

func TestPlanModeBlocksBash(t *testing.T) {
	SetPlanMode(true)
	defer SetPlanMode(false)

	tool := NewBashTool(nil)
	resp, err := tool.Run(context.Background(), ToolCall{
		ID:    "t1",
		Name:  BashToolName,
		Input: `{"command":"echo hi"}`,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.IsError || resp.Content != planModeRefusal {
		t.Fatalf("bash should be refused in plan mode, got %+v", resp)
	}
}
