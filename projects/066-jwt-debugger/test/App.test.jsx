/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from '../src/App.jsx';
import { SAMPLE_TOKEN } from '../src/sample.js';

afterEach(cleanup);
const NOW = 1_800_000_000;

describe('<App />', () => {
  it('decodes the sample token and verifies its signature', async () => {
    render(<App now={NOW} />);
    const payload = screen.getByLabelText('Payload');
    expect(within(payload).getByText('"Ada Lovelace"')).toBeTruthy();
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('Signature verified'));
    expect(screen.getByText('Time claims OK')).toBeTruthy();
  });

  it('shows an invalid signature when the secret changes', async () => {
    render(<App now={NOW} />);
    fireEvent.change(screen.getByLabelText('Shared secret'), { target: { value: 'nope' } });
    await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/Invalid signature/));
  });

  it('reports malformed tokens', () => {
    render(<App now={NOW} />);
    fireEvent.change(screen.getByLabelText('Encoded token'), { target: { value: 'not-a-token' } });
    expect(screen.getByRole('alert').textContent).toMatch(/3 dot-separated parts/);
  });

  it('marks the sample as expired far in the future', () => {
    render(<App now={4_200_000_000} />);
    expect(screen.getByText('Expired')).toBeTruthy();
  });

  it('encodes a token and opens it in the debugger', async () => {
    render(<App initialToken={SAMPLE_TOKEN} now={Math.floor(Date.now() / 1000)} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Encode' }));
    fireEvent.change(screen.getByLabelText('Secret'), { target: { value: 'roundtrip' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign' }));
    await screen.findByLabelText('Signed token');
    fireEvent.click(screen.getByRole('button', { name: 'Open in debugger' }));
    expect(within(screen.getByLabelText('Payload')).getByText('"user-42"')).toBeTruthy();
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('Signature verified'));
  });
});
