package device

import "testing"

func TestCandidateRoots(t *testing.T) {
	roots := getCandidateRoots()
	if roots == nil {
		t.Errorf("roots should not be nil")
	}
}
