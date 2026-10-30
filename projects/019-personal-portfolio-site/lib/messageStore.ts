import type { ContactInput } from "./validation";

/**
 * Where accepted contact messages go.
 *
 * The default store keeps messages in memory and logs them, so the project runs
 * with zero configuration and no secrets. Swap in an implementation that sends
 * email (Resend, SES, SMTP) or writes to a database for production.
 */
export interface StoredMessage extends ContactInput {
  id: string;
  receivedAt: string;
}

export interface MessageStore {
  save(msg: ContactInput): Promise<StoredMessage>;
  list(): Promise<StoredMessage[]>;
}

export class InMemoryMessageStore implements MessageStore {
  private messages: StoredMessage[] = [];
  private counter = 0;

  async save(msg: ContactInput): Promise<StoredMessage> {
    const stored: StoredMessage = {
      name: msg.name,
      email: msg.email,
      message: msg.message,
      id: `msg_${++this.counter}`,
      receivedAt: new Date().toISOString(),
    };
    this.messages.push(stored);
    return stored;
  }

  async list(): Promise<StoredMessage[]> {
    return [...this.messages];
  }
}
