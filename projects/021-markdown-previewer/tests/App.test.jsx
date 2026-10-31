import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App.jsx';
import { readAsText } from '../src/lib/exportHtml.js';

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

const editor = () => screen.getByLabelText('Markdown editor');
const preview = () => screen.getByTestId('preview');

describe('<App />', () => {
  it('renders the sample document in both panes', () => {
    render(<App />);
    expect(editor().value).toContain('# Markdown Previewer');
    expect(preview().querySelector('h1').textContent).toBe('Markdown Previewer');
    expect(preview().querySelector('table')).not.toBeNull();
  });

  it('updates the preview live as the user types', () => {
    render(<App />);
    fireEvent.change(editor(), { target: { value: '## Live\n\n**bold** text' } });
    expect(preview().innerHTML).toBe('<h2 id="live">Live</h2>\n<p><strong>bold</strong> text</p>\n');
    expect(screen.getByText(/3 words/)).toBeTruthy();
  });

  it('never injects raw HTML from the source', () => {
    render(<App />);
    fireEvent.change(editor(), { target: { value: '<img src=x onerror="alert(1)">' } });
    expect(preview().querySelector('img')).toBeNull();
    expect(preview().textContent).toContain('<img src=x');
  });

  it('switches between editor, split and preview layouts', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('radio', { name: 'Preview' }));
    expect(screen.queryByLabelText('Markdown editor')).toBeNull();
    fireEvent.click(screen.getByRole('radio', { name: 'Editor' }));
    expect(screen.queryByTestId('preview')).toBeNull();
    fireEvent.click(screen.getByRole('radio', { name: 'Split' }));
    expect(editor()).toBeTruthy();
    expect(preview()).toBeTruthy();
  });

  it('bolds the selection with Ctrl+B and the toolbar toggles it back', () => {
    render(<App initialSource="hello world" />);
    const ta = editor();
    ta.setSelectionRange(6, 11);
    fireEvent.keyDown(ta, { key: 'b', ctrlKey: true });
    expect(ta.value).toBe('hello **world**');
    expect(ta.value.slice(ta.selectionStart, ta.selectionEnd)).toBe('world');
    fireEvent.click(screen.getByRole('button', { name: /Bold/ }));
    expect(ta.value).toBe('hello world');
  });

  it('inserts spaces on Tab instead of moving focus', () => {
    render(<App initialSource="- a" />);
    const ta = editor();
    ta.setSelectionRange(0, 0);
    fireEvent.keyDown(ta, { key: 'Tab' });
    expect(ta.value).toBe('  - a');
    fireEvent.keyDown(ta, { key: 'Tab', shiftKey: true });
    expect(ta.value).toBe('- a');
  });

  it('exports a standalone HTML file named after the title', async () => {
    const createObjectURL = vi.fn(() => 'blob:mock');
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(<App initialSource={'# Trip Notes\n\nDay *one*'} />);
    fireEvent.click(screen.getByRole('button', { name: 'Export HTML' }));

    expect(click).toHaveBeenCalledTimes(1);
    const anchor = click.mock.contexts[0];
    expect(anchor.download).toBe('trip-notes.html');
    const blob = createObjectURL.mock.calls[0][0];
    const text = await readAsText(blob);
    expect(text).toContain('<title>Trip Notes</title>');
    expect(text).toContain('<p>Day <em>one</em></p>');
    expect(screen.getByRole('status').textContent).toBe('Exported HTML');
  });

  it('copies HTML to the clipboard', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    render(<App initialSource="*hi*" />);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Copy HTML' }));
    });
    expect(writeText).toHaveBeenCalledWith('<p><em>hi</em></p>\n');
    expect(screen.getByRole('status').textContent).toBe('HTML copied to clipboard');
  });

  it('persists the document to localStorage and restores it', async () => {
    vi.useFakeTimers();
    const { unmount } = render(<App />);
    fireEvent.change(editor(), { target: { value: 'saved text' } });
    act(() => vi.advanceTimersByTime(400));
    expect(JSON.parse(window.localStorage.getItem('markdown-previewer:source'))).toBe('saved text');
    unmount();
    render(<App />);
    expect(editor().value).toBe('saved text');
  });

  it('opens a Markdown file from disk', async () => {
    render(<App />);
    const file = new File(['# From disk'], 'notes.md', { type: 'text/markdown' });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(editor().value).toBe('# From disk'));
    expect(preview().querySelector('h1').textContent).toBe('From disk');
  });
});
