import { gmail_v1 } from '@googleapis/gmail';
import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import * as fs from 'fs';
import * as path from 'fs';
import { z } from 'zod';
import { createLogger, transports, format } from 'winston';
import { TokenBucket } from 'token-bucket';
import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Logger configuration
 */
const logger = createLogger({
  level: 'info',
  format: format.combine(format.timestamp(), format.json()),
  transports: [new transports.File({ filename: 'gmail-mcp.log' })],
});

/**
 * Configuration storage
 */
const CONFIG_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '.', '.gmail-mcp');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
interface Config {
  activeAccount: string | null;
}
let config: Config = { activeAccount: process.env.GOOGLE_DEFAULT_ACCOUNT || null };
if (!fs.existsSync(CONFIG_DIR)) {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
}
if (fs.existsSync(CONFIG_FILE)) {
  config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
}

/**
 * Gmail API client
 */
const oauth2Client = new OAuth2Client({
  clientId: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  redirectUri: 'http://localhost:4100/code',
});
const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

/**
 * Rate limiter for Gmail API quotas
 */
const rateLimiter = new TokenBucket({
  capacity: 250,
  fillRate: 250,
  interval: 1000,
});

/**
 * Account storage
 */
interface Account {
  email: string;
  token: string;
}
const ACCOUNTS_FILE = path.join(CONFIG_DIR, 'accounts.json');
let accounts: Account[] = [];
if (fs.existsSync(ACCOUNTS_FILE)) {
  accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE, 'utf-8'));
}

/**
 * Get Gmail client for an account
 * @param email - Gmail account email address
 * @returns Gmail API client
 */
async function getGmailClient(email: string): Promise<gmail_v1.Gmail> {
  const account = accounts.find(acc => acc.email === email);
  if (!account) throw new Error(`No account found for ${email}`);
  oauth2Client.setCredentials({ access_token: account.token });
  return google.gmail({ version: 'v1', auth: oauth2Client });
}

/**
 * Tool schemas
 */
const EmailSchema = z.object({
  accountEmail: z.string().email().optional(),
  to: z.array(z.string().email()).min(1),
  subject: z.string().min(1),
  body: z.string().min(1),
  cc: z.array(z.string().email()).optional(),
  bcc: z.array(z.string().email()).optional(),
  mimeType: z.enum(['text/plain', 'text/html']).optional().default('text/plain'),
});
const MessageIdSchema = z.object({
  accountEmail: z.string().email().optional(),
  messageId: z.string().min(1),
});
const ThreadIdSchema = z.object({
  accountEmail: z.string().email().optional(),
  threadId: z.string().min(1),
});
const SearchSchema = z.object({
  accountEmail: z.string().email().optional(),
  query: z.string().min(1),
  maxResults: z.number().int().positive().optional().default(10),
});
const LabelSchema = z.object({
  accountEmail: z.string().email().optional(),
  messageId: z.string().min(1),
  labelIds: z.array(z.string().min(1)).min(1),
});
const CreateLabelSchema = z.object({
  accountEmail: z.string().email().optional(),
  name: z.string().min(1),
  labelListVisibility: z.enum(['labelShow', 'labelShowIfUnread', 'labelHide']).optional(),
});
const ListAccountsSchema = z.object({});
const SetAccountSchema = z.object({
  accountEmail: z.string().email(),
});
const GetAccountInfoSchema = z.object({});

/**
 * Define a tool with schema and handler
 */
interface Tool {
  name: string;
  description: string;
  inputSchema: z.ZodSchema;
  handler: (params: { input: any }) => Promise<{ result: any }>;
}

/**
 * Gmail MCP tools
 */
export const tools: Tool[] = [
  {
    name: 'send_email',
    description: 'Send an email with optional CC and BCC recipients',
    inputSchema: EmailSchema,
    async handler({ input }) {
      await rateLimiter.take(100);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      const raw = Buffer.from(
        `From: ${email}\r\n` +
        `To: ${input.to.join(',')}\r\n` +
        (input.cc ? `Cc: ${input.cc.join(',')}\r\n` : '') +
        (input.bcc ? `Bcc: ${input.bcc.join(',')}\r\n` : '') +
        `Subject: ${input.subject}\r\n` +
        `Content-Type: ${input.mimeType}; charset=utf-8\r\n\r\n` +
        input.body
      ).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
      const res = await client.users.messages.send({
        userId: 'me',
        requestBody: { raw },
      });
      logger.info(`Sent email from ${email} to ${input.to.join(',')}`);
      return { result: { messageId: res.data.id } };
    },
  },
  {
    name: 'read_today_emails',
    description: 'Fetch emails received today',
    inputSchema: ListAccountsSchema,
    async handler({ input }) {
      await rateLimiter.take(50);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      const today = new Date().toISOString().split('T')[0];
      const res = await client.users.messages.list({ userId: 'me', q: `from:${today}` });
      const messages = await Promise.all(
        (res.data.messages || []).map(async msg => {
          const message = await client.users.messages.get({ userId: 'me', id: msg.id! });
          return {
            id: msg.id,
            snippet: message.data.snippet,
            subject: message.data.payload?.headers?.find(h => h.name.toLowerCase() === 'subject')?.value,
            from: message.data.payload?.headers?.find(h => h.name.toLowerCase() === 'from')?.value,
          };
        })
      );
      logger.info(`Fetched ${messages.length} emails from ${email} for today`);
      return { result: messages };
    },
  },
  {
    name: 'read_email',
    description: 'Read a specific email by message ID',
    inputSchema: MessageIdSchema,
    async handler({ input }) {
      await rateLimiter.take(50);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      const res = await client.users.messages.get({ userId: 'me', id: input.messageId });
      logger.info(`Read email ${input.messageId} from ${email}`);
      return {
        result: {
          id: res.data.id,
          snippet: res.data.snippet,
          subject: res.data.payload?.headers?.find(h => h.name.toLowerCase() === 'subject')?.value,
          from: res.data.payload?.headers?.find(h => h.name.toLowerCase() === 'from')?.value,
          body: res.data.payload?.parts?.[0]?.body?.data || res.data.payload?.body?.data,
        },
      };
    },
  },
  {
    name: 'read_thread',
    description: 'Read an email thread by thread ID',
    inputSchema: ThreadIdSchema,
    async handler({ input }) {
      await rateLimiter.take(100);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      const res = await client.users.threads.get({ userId: 'me', id: input.threadId });
      logger.info(`Read thread ${input.threadId} from ${email}`);
      return { result: res.data };
    },
  },
  {
    name: 'delete_email',
    description: 'Permanently delete an email by message ID',
    inputSchema: MessageIdSchema,
    async handler({ input }) {
      await rateLimiter.take(100);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      await client.users.messages.delete({ userId: 'me', id: input.messageId });
      logger.info(`Deleted email ${input.messageId} from ${email}`);
      return { result: { success: true } };
    },
  },
  {
    name: 'archive_email',
    description: 'Archive an email by removing the INBOX label',
    inputSchema: MessageIdSchema,
    async handler({ input }) {
      await rateLimiter.take(50);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      await client.users.messages.modify({
        userId: 'me',
        id: input.messageId,
        requestBody: { removeLabelIds: ['INBOX'] },
      });
      logger.info(`Archived email ${input.messageId} from ${email}`);
      return { result: { success: true } };
    },
  },
  {
    name: 'create_draft',
    description: 'Create a draft email',
    inputSchema: EmailSchema,
    async handler({ input }) {
      await rateLimiter.take(100);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      const raw = Buffer.from(
        `From: ${email}\r\n` +
        `To: ${input.to.join(',')}\r\n` +
        (input.cc ? `Cc: ${input.cc.join(',')}\r\n` : '') +
        (input.bcc ? `Bcc: ${input.bcc.join(',')}\r\n` : '') +
        `Subject: ${input.subject}\r\n` +
        `Content-Type: ${input.mimeType}; charset=utf-8\r\n\r\n` +
        input.body
      ).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
      const res = await client.users.drafts.create({
        userId: 'me',
        requestBody: { message: { raw } },
      });
      logger.info(`Created draft for ${email}`);
      return { result: { id: res.data.id } };
    },
  },
  {
    name: 'add_label',
    description: 'Add labels to an email',
    inputSchema: LabelSchema,
    async handler({ input }) {
      await rateLimiter.take(50);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      await client.users.messages.modify({
        userId: 'me',
        id: input.messageId,
        requestBody: { addLabelIds: input.labelIds },
      });
      logger.info(`Added labels to email ${input.messageId} from ${email}`);
      return { result: { success: true } };
    },
  },
  {
    name: 'remove_label',
    description: 'Remove labels from an email',
    inputSchema: LabelSchema,
    async handler({ input }) {
      await rateLimiter.take(50);
      const email = input.accountEmail || config.activeAccount;
      if (!email) throw new Error('No active account set');
      const client = await getGmailClient(email);
      await client.users.messages.modify({
        userId: 'me',
        id: input.messageId,
        request