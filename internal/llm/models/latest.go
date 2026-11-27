package models

import "maps"

// Latest model IDs, prices in USD per 1M tokens.
// Sources: provider pricing/model pages (Anthropic, OpenAI, Google), Nov 2026.
const (
	// Anthropic
	Claude5Fable  ModelID = "claude-fable-5.2"
	Claude5Opus   ModelID = "claude-opus-5.5"
	Claude5Sonnet ModelID = "claude-sonnet-5.5"
	Claude5Haiku  ModelID = "claude-haiku-5.5"

	// OpenAI
	GPT62Astra ModelID = "gpt-6.2-astra"
	GPT62Sol   ModelID = "gpt-6.2-sol"
	GPT61Terra ModelID = "gpt-6.1-terra"
	GPT6Luna   ModelID = "gpt-6-luna"

	// Google Gemini
	Gemini35Flash      ModelID = "gemini-3.5-flash"
	Gemini31FlashLite  ModelID = "gemini-3.1-flash-lite"
	Gemini31ProPreview ModelID = "gemini-3.1-pro-preview"
)

// LatestModels are merged into SupportedModels at startup.
var LatestModels = map[ModelID]Model{
	Claude5Fable: {
		ID:                  Claude5Fable,
		Name:                "Claude Fable 5.2",
		Provider:            ProviderAnthropic,
		APIModel:            "claude-fable-5-2",
		CostPer1MIn:         8.0,
		CostPer1MInCached:   10.0,
		CostPer1MOutCached:  0.20,
		CostPer1MOut:        40.0,
		ContextWindow:       1000000,
		DefaultMaxTokens:    16000,
		SupportsAttachments: true,
	},
	Claude5Opus: {
		ID:                  Claude5Opus,
		Name:                "Claude Opus 5.5",
		Provider:            ProviderAnthropic,
		APIModel:            "claude-opus-5-5",
		CostPer1MIn:         4.0,
		CostPer1MInCached:   5.0,
		CostPer1MOutCached:  0.20,
		CostPer1MOut:        20.0,
		ContextWindow:       1000000,
		DefaultMaxTokens:    16000,
		SupportsAttachments: true,
	},
	Claude5Sonnet: {
		ID:                  Claude5Sonnet,
		Name:                "Claude Sonnet 5.5",
		Provider:            ProviderAnthropic,
		APIModel:            "claude-sonnet-5-5",
		CostPer1MIn:         2.0,
		CostPer1MInCached:   2.5,
		CostPer1MOutCached:  0.10,
		CostPer1MOut:        10.0,
		ContextWindow:       1000000,
		DefaultMaxTokens:    16000,
		SupportsAttachments: true,
	},
	Claude5Haiku: {
		ID:                  Claude5Haiku,
		Name:                "Claude Haiku 5.5",
		Provider:            ProviderAnthropic,
		APIModel:            "claude-haiku-5-5",
		CostPer1MIn:         0.10,
		CostPer1MInCached:   0.125,
		CostPer1MOutCached:  0.01,
		CostPer1MOut:        0.50,
		ContextWindow:       200000,
		DefaultMaxTokens:    8000,
		SupportsAttachments: true,
	},

	GPT62Astra: {
		ID:                  GPT62Astra,
		Name:                "GPT 6.2 Astra",
		Provider:            ProviderOpenAI,
		APIModel:            "gpt-6.2-astra",
		CostPer1MIn:         8.0,
		CostPer1MOut:        40.0,
		ContextWindow:       1050000,
		DefaultMaxTokens:    32000,
		CanReason:           true,
		SupportsAttachments: true,
	},
	GPT62Sol: {
		ID:                  GPT62Sol,
		Name:                "GPT 6.2 Sol",
		Provider:            ProviderOpenAI,
		APIModel:            "gpt-6.2-sol",
		CostPer1MIn:         2.0,
		CostPer1MOut:        10.0,
		ContextWindow:       1050000,
		DefaultMaxTokens:    32000,
		CanReason:           true,
		SupportsAttachments: true,
	},
	GPT61Terra: {
		ID:                  GPT61Terra,
		Name:                "GPT 6.1 Terra",
		Provider:            ProviderOpenAI,
		APIModel:            "gpt-6.1-terra",
		CostPer1MIn:         1.0,
		CostPer1MOut:        5.0,
		ContextWindow:       1050000,
		DefaultMaxTokens:    32000,
		CanReason:           true,
		SupportsAttachments: true,
	},
	GPT6Luna: {
		ID:                  GPT6Luna,
		Name:                "GPT 6 Luna",
		Provider:            ProviderOpenAI,
		APIModel:            "gpt-6-luna",
		CostPer1MIn:         0.10,
		CostPer1MOut:        0.50,
		ContextWindow:       1050000,
		DefaultMaxTokens:    16000,
		CanReason:           true,
		SupportsAttachments: true,
	},

	Gemini35Flash: {
		ID:                  Gemini35Flash,
		Name:                "Gemini 3.5 Flash",
		Provider:            ProviderGemini,
		APIModel:            "gemini-3.5-flash",
		CostPer1MIn:         1.50,
		CostPer1MInCached:   0,
		CostPer1MOutCached:  0.15,
		CostPer1MOut:        9.0,
		ContextWindow:       1000000,
		DefaultMaxTokens:    16000,
		SupportsAttachments: true,
	},
	Gemini31FlashLite: {
		ID:                  Gemini31FlashLite,
		Name:                "Gemini 3.1 Flash-Lite",
		Provider:            ProviderGemini,
		APIModel:            "gemini-3.1-flash-lite",
		CostPer1MIn:         0.25,
		CostPer1MInCached:   0,
		CostPer1MOutCached:  0.025,
		CostPer1MOut:        1.50,
		ContextWindow:       1000000,
		DefaultMaxTokens:    8000,
		SupportsAttachments: true,
	},
	Gemini31ProPreview: {
		ID:                  Gemini31ProPreview,
		Name:                "Gemini 3.1 Pro (preview)",
		Provider:            ProviderGemini,
		APIModel:            "gemini-3.1-pro-preview",
		CostPer1MIn:         2.0,
		CostPer1MInCached:   0,
		CostPer1MOutCached:  0.20,
		CostPer1MOut:        12.0,
		ContextWindow:       1000000,
		DefaultMaxTokens:    16000,
		SupportsAttachments: true,
	},
}

func init() {
	maps.Copy(SupportedModels, LatestModels)
}
