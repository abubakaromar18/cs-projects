package protocol

import (
	"errors"
	"testing"
)

func TestParse(t *testing.T) {
	tests := []struct {
		name string
		line string
		want Command
		err  error
	}{
		{"say", "hello world", Command{Kind: KindSay, Text: "hello world"}, nil},
		{"say strips CRLF", "hi\r\n", Command{Kind: KindSay, Text: "hi"}, nil},
		{"empty", "   ", Command{}, ErrEmpty},
		{"nick", "/nick bob", Command{Kind: KindNick, Target: "bob"}, nil},
		{"nick case-insensitive verb", "/NICK bob", Command{Kind: KindNick, Target: "bob"}, nil},
		{"nick missing", "/nick", Command{}, ErrMissingArg},
		{"nick invalid", "/nick bad name!", Command{}, ErrBadNick},
		{"msg", "/msg bob are you there?", Command{Kind: KindMsg, Target: "bob", Text: "are you there?"}, nil},
		{"msg no text", "/msg bob", Command{}, ErrMissingArg},
		{"me", "/me waves", Command{Kind: KindMe, Text: "waves"}, nil},
		{"me missing", "/me", Command{}, ErrMissingArg},
		{"who", "/who", Command{Kind: KindWho}, nil},
		{"help", "/help", Command{Kind: KindHelp}, nil},
		{"quit", "/quit", Command{Kind: KindQuit}, nil},
		{"unknown", "/dance", Command{}, ErrUnknownCommand},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Parse(tt.line)
			if !errors.Is(err, tt.err) {
				t.Fatalf("Parse(%q) err = %v, want %v", tt.line, err, tt.err)
			}
			if got != tt.want {
				t.Fatalf("Parse(%q) = %+v, want %+v", tt.line, got, tt.want)
			}
		})
	}
}

func TestValidateNick(t *testing.T) {
	good := []string{"a", "alice", "Bob_42", "x-y", "émile", "abcdefghijklmnop"}
	bad := []string{"", "has space", "semi;colon", "abcdefghijklmnopq", "tab\t"}
	for _, n := range good {
		if err := ValidateNick(n); err != nil {
			t.Errorf("ValidateNick(%q) = %v, want nil", n, err)
		}
	}
	for _, n := range bad {
		if err := ValidateNick(n); err == nil {
			t.Errorf("ValidateNick(%q) = nil, want error", n)
		}
	}
}
