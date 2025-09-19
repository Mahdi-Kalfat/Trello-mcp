import * as fs from 'fs';
import * as path from 'fs';
import { createLogger, transports, format } from 'winston';
import { tools } from './tools';
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
 * Main CLI handler for LLM agent integration
 */
async function main() {
  const args = process.argv.slice(2);
  logger.info(`Raw process.argv: ${JSON.stringify(process.argv)}`);

  if (args.length < 1) {
    console.error('[ERROR] No tool name provided');
    process.exit(1);
  }

  const toolName = args[0];
  const tool = tools.find(t => t.name === toolName);
  if (!tool) {
    console.error(`[ERROR] Tool ${toolName} not found`);
    process.exit(1);
  }

  let toolArgs: any = {};
  if (args[1]) {
    try {
      toolArgs = JSON.parse(args[1]);
    } catch (error) {
      console.error(`[ERROR] Invalid arguments format. Expected a valid JSON string, got: ${args[1]}`);
      process.exit(1);
    }
  }

  try {
    const validatedArgs = tool.inputSchema.parse(toolArgs);
    const result = await tool.handler({ input: validatedArgs });
    console.log(`[INFO] Result: ${JSON.stringify(result)}`);
  } catch (error) {
    console.error(`[ERROR] ${error instanceof Error ? error.message : 'Unknown error'}`);
    process.exit(1);
  }
}

main().catch(error => {
  console.error(`[ERROR] ${error.message}`);
  process.exit(1);
});