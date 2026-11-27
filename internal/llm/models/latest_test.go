package models

import "testing"

func TestLatestModelsRegistered(t *testing.T) {
	for id, m := range LatestModels {
		got, ok := SupportedModels[id]
		if !ok {
			t.Errorf("%s missing from SupportedModels", id)
			continue
		}
		if got.ID != id || got.APIModel == "" || got.Provider == "" {
			t.Errorf("%s has incomplete definition: %+v", id, got)
		}
		if m.ContextWindow <= 0 || m.DefaultMaxTokens <= 0 {
			t.Errorf("%s needs context window and max tokens", id)
		}
	}
}
