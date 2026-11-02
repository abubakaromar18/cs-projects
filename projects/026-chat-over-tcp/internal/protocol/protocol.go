// Package protocol defines the tiny line-oriented text protocol spoken
// between the chat server and its clients.
//
// Every message is a single UTF-8 line terminated by '\n'. A line that
// starts with '/' is a command; anything else is a chat message that the
// server broadcasts to every other connected user.
//
//	/nick <name>         change your nickname
//	/msg <name> <text>   send a private message
//	/who                 list connected users
//	/me <action>         emote ("* alice waves")
//	/help                show the command list
//	/quit                disconnect
package protocol

import (
	"errors"
	"fmt"
	"strings"
	"unicode"
)

// Kind identifies what a parsed client line asks the server to do.
type Kind int

const (
	KindSay Kind = iota // plain chat message to everyone
	KindNick
	KindMsg
	KindWho
	KindMe
	KindHelp
	KindQuit
)

// MaxNickLen bounds nickname length so one client can't flood the user list.
const MaxNickLen = 16

// MaxLineLen is the largest line (in bytes) the server will accept.
const MaxLineLen = 1024

// Command is the structured form of one line sent by a client.
type Command struct {
	Kind   Kind
	Target string // nickname for /nick and /msg
	Text   string // message body for say, /msg and /me
}

// Errors returned by Parse and ValidateNick.
var (
	ErrEmpty          = errors.New("empty message")
	ErrUnknownCommand = errors.New("unknown command")
	ErrMissingArg     = errors.New("missing argument")
	ErrBadNick        = errors.New("nickname must be 1-16 letters, digits, '_' or '-'")
)

// HelpText is sent in response to /help.
const HelpText = `Commands:
  /nick <name>        change your nickname
  /msg <name> <text>  private message
  /who                list users
  /me <action>        emote
  /help               this help
  /quit               leave the chat`

// Parse converts a raw line (without the trailing newline) into a Command.
func Parse(line string) (Command, error) {
	line = strings.TrimRight(line, "\r\n")
	if strings.TrimSpace(line) == "" {
		return Command{}, ErrEmpty
	}
	if !strings.HasPrefix(line, "/") {
		return Command{Kind: KindSay, Text: line}, nil
	}

	// Split "/cmd rest of line" into the verb and its argument string.
	verb, rest, _ := strings.Cut(line[1:], " ")
	rest = strings.TrimSpace(rest)

	switch strings.ToLower(verb) {
	case "nick":
		if rest == "" {
			return Command{}, fmt.Errorf("/nick: %w", ErrMissingArg)
		}
		if err := ValidateNick(rest); err != nil {
			return Command{}, err
		}
		return Command{Kind: KindNick, Target: rest}, nil
	case "msg":
		target, text, ok := strings.Cut(rest, " ")
		text = strings.TrimSpace(text)
		if !ok || target == "" || text == "" {
			return Command{}, fmt.Errorf("/msg: %w (usage: /msg <name> <text>)", ErrMissingArg)
		}
		return Command{Kind: KindMsg, Target: target, Text: text}, nil
	case "me":
		if rest == "" {
			return Command{}, fmt.Errorf("/me: %w", ErrMissingArg)
		}
		return Command{Kind: KindMe, Text: rest}, nil
	case "who":
		return Command{Kind: KindWho}, nil
	case "help":
		return Command{Kind: KindHelp}, nil
	case "quit":
		return Command{Kind: KindQuit}, nil
	}
	return Command{}, fmt.Errorf("%w: /%s (try /help)", ErrUnknownCommand, verb)
}

// ValidateNick reports whether name is an acceptable nickname.
func ValidateNick(name string) error {
	if len(name) == 0 || len(name) > MaxNickLen {
		return ErrBadNick
	}
	for _, r := range name {
		if !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-') {
			return ErrBadNick
		}
	}
	return nil
}
