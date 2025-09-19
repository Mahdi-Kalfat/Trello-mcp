import dotenv from 'dotenv';
import { connectDB } from './config/db';
import app from './server';

dotenv.config();

const PORT = process.env.PORT || 8000;

const startServer = async () => {
    await connectDB();
    app.listen(PORT, () => {
        console.log(`MCP Server running on port ${PORT}`);
    });
};

startServer();