package cmd

import (
	"archive/tar"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/superneo121-byte/Pro-Code-CLI-procode-/internal/version"
)

const releaseRepo = "superneo121-byte/Pro-Code-CLI-procode-"

var upgradeCmd = &cobra.Command{
	Use:   "upgrade",
	Short: "Upgrade procode to the latest GitHub release",
	Long:  "Downloads the latest release from GitHub and replaces the running procode binary.",
	RunE: func(cmd *cobra.Command, args []string) error {
		return runUpgrade()
	},
}

func init() {
	rootCmd.AddCommand(upgradeCmd)
}

type ghRelease struct {
	TagName string `json:"tag_name"`
	Assets  []struct {
		Name string `json:"name"`
		URL  string `json:"browser_download_url"`
	} `json:"assets"`
}

// archiveName mirrors the name_template in .goreleaser.yml.
func archiveName() string {
	osName := runtime.GOOS
	if osName == "darwin" {
		osName = "mac"
	}
	arch := runtime.GOARCH
	if arch == "amd64" {
		arch = "x86_64"
	}
	return fmt.Sprintf("procode-%s-%s.tar.gz", osName, arch)
}

func runUpgrade() error {
	client := &http.Client{Timeout: 2 * time.Minute}

	resp, err := client.Get("https://api.github.com/repos/" + releaseRepo + "/releases/latest")
	if err != nil {
		return fmt.Errorf("could not reach GitHub: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return fmt.Errorf("no release found yet at github.com/%s/releases", releaseRepo)
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("GitHub returned %s", resp.Status)
	}
	var rel ghRelease
	if err := json.NewDecoder(resp.Body).Decode(&rel); err != nil {
		return fmt.Errorf("could not read release info: %w", err)
	}

	latest := strings.TrimPrefix(rel.TagName, "v")
	current := strings.TrimPrefix(version.Version, "v")
	if latest == current {
		fmt.Printf("Already up to date (%s)\n", version.Version)
		return nil
	}

	want := archiveName()
	var url string
	for _, a := range rel.Assets {
		if a.Name == want {
			url = a.URL
			break
		}
	}
	if url == "" {
		return fmt.Errorf("release %s has no file named %s for this system", rel.TagName, want)
	}

	fmt.Printf("Downloading %s (%s)...\n", rel.TagName, want)
	dl, err := client.Get(url)
	if err != nil {
		return fmt.Errorf("download failed: %w", err)
	}
	defer dl.Body.Close()
	if dl.StatusCode != http.StatusOK {
		return fmt.Errorf("download failed: %s", dl.Status)
	}

	exe, err := os.Executable()
	if err != nil {
		return err
	}
	if resolved, err := filepath.EvalSymlinks(exe); err == nil {
		exe = resolved
	}

	gz, err := gzip.NewReader(dl.Body)
	if err != nil {
		return fmt.Errorf("bad archive: %w", err)
	}
	tr := tar.NewReader(gz)

	tmp := exe + ".new"
	found := false
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("bad archive: %w", err)
		}
		if hdr.Typeflag != tar.TypeReg || filepath.Base(hdr.Name) != "procode" {
			continue
		}
		f, err := os.OpenFile(tmp, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o755)
		if err != nil {
			return fmt.Errorf("cannot write next to %s: %w", exe, err)
		}
		if _, err := io.Copy(f, tr); err != nil {
			f.Close()
			os.Remove(tmp)
			return err
		}
		if err := f.Close(); err != nil {
			os.Remove(tmp)
			return err
		}
		found = true
		break
	}
	if !found {
		return fmt.Errorf("archive did not contain a procode binary")
	}

	if err := os.Rename(tmp, exe); err != nil {
		os.Remove(tmp)
		return fmt.Errorf("could not replace %s: %w", exe, err)
	}
	fmt.Printf("Upgraded to %s\n", rel.TagName)
	return nil
}
