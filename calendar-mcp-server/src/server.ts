import express from 'express';
import cors from 'cors';
import { calendarTools } from './tools/calendarTools';
import { calendarToolHandlers } from './tools/calendarToolHandlers';
import { ToolCall } from './types/calendarTypes';

const app = express();
app.use(cors());
app.use(express.json());

// SSE endpoint for MCP
app.get('/sse', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Send session ID
    const sessionId = Math.random().toString(36).substring(2);
    res.write(`data: session_id=${sessionId}\n\n`);

    // Send tools list
    res.write(`data: ${JSON.stringify({ tools: calendarTools })}\n\n`);

    // Keep connection alive
    const keepAlive = setInterval(() => {
        res.write('data: keep-alive\n\n');
    }, 15000);

    req.on('close', () => {
        clearInterval(keepAlive);
        res.end();
    });
});

// Message endpoint to handle tool calls
app.post('/messages', async (req, res) => {
    const { session_id, content } = req.body;
    if (!session_id || !content || !content.tool_calls) {
        return res.status(400).json({ error: 'Invalid request' });
    }

    const toolCalls: ToolCall[] = content.tool_calls;
    const results = [];

    for (const toolCall of toolCalls) {
        const handler = (calendarToolHandlers as any)[toolCall.name];
        if (!handler) {
            results.push({ error: `Tool ${toolCall.name} not found` });
            continue;
        }

        try {
            const result = await handler(toolCall.arguments);
            results.push({ tool: toolCall.name, result });
        } catch (error) {
            results.push({ tool: toolCall.name, error: (error as Error).message });
        }
    }

    res.json({ results });
});

export default app;