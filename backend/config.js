// backend/config.js
export const mongoUri = process.env.MONGO_URI || 'mongodb://localhost:27017/trello_mcp';
export const calendarDbName = process.env.CALENDAR_DB_NAME || 'calendar_mcp_db';
