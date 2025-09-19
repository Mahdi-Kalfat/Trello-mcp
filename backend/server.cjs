// backend/server.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { mongoUri } = require('./config');

const app = express();
app.use(cors());
app.use(express.json());

mongoose.connect(mongoUri, { useNewUrlParser: true, useUnifiedTopology: true });

mongoose.connection.once('open', () => {
  console.log('MongoDB connection established to test_mcp/sessions');
});

// Use the 'sessions' collection in test_mcp, non-strict schema
const sessionSchema = new mongoose.Schema({
  session_id: String,
  started_at: Date,
  interactions: [
    {
      prompt: String,
      prompt_time: Date,
      response: String,
      response_time: Date,
      pending_tool: mongoose.Schema.Types.Mixed,
      pending_type: mongoose.Schema.Types.Mixed,
      pending_name: mongoose.Schema.Types.Mixed,
      pending_options: mongoose.Schema.Types.Mixed
    }
  ],
  cache: Array
}, { collection: 'sessions', strict: false });

const Session = mongoose.model('Session', sessionSchema, 'sessions');

// User schema for trello_mcp.users (no id field, only email unique)
const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true }
}, { collection: 'users' });

const User = mongoose.model('User', userSchema, 'users');

// Calendar events endpoint (calendar_mcp_db.events)
app.get('/api/calendar-events', async (req, res) => {
  try {
    const calendarDb = mongoose.connection.useDb('calendar_mcp_db');
    const eventSchema = new mongoose.Schema({
      title: String,
      date: String,
      description: String
    }, { collection: 'events' });
    const Event = calendarDb.model('Event', eventSchema, 'events');
    const events = await Event.find({});
    res.json(events);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
// Register endpoint (no id field, only email unique)
app.post('/api/register', async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password) return res.status(400).json({ message: 'All fields required' });
  try {
    const userDb = mongoose.connection.useDb('trello_mcp');
    const UserModel = userDb.model('User', userSchema, 'users');
    // Only check for existing email
    const existing = await UserModel.findOne({ email });
    if (existing) return res.status(400).json({ message: 'Email already registered' });
    await UserModel.create({ name, email, password });
    res.status(200).json({ message: 'Account created' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Login endpoint (no id field)
app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ message: 'All fields required' });
  try {
    const userDb = mongoose.connection.useDb('trello_mcp');
    const UserModel = userDb.model('User', userSchema, 'users');
    const user = await UserModel.findOne({ email });
    if (!user || user.password !== password) return res.status(401).json({ message: 'Invalid credentials' });
    res.status(200).json({ message: 'Login successful', user: { name: user.name, email: user.email } });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});


// Get all sessions (old chats)
app.get('/api/chats', async (req, res) => {
  console.log('GET /api/chats called');
  try {
    const sessions = await Session.find();
    console.log('All session_ids in DB:', sessions.map(s => s.session_id));
    // Structure response: session_id, messages [{ sender, text, time }], cache_updated_at
    const result = sessions.map(session => ({
      session_id: session.session_id,
      cache_updated_at: session.cache_updated_at || null,
      messages: session.interactions.flatMap(interaction => [
        {
          sender: 'user',
          text: interaction.prompt,
          time: interaction.prompt_time
        },
        {
          sender: 'ai',
          text: interaction.response,
          time: interaction.response_time
        }
      ])
    }));
    console.log('GET /api/chats response:', JSON.stringify(result, null, 2));
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get a single session by session_id
app.get('/api/chats/:session_id', async (req, res) => {
  const { session_id } = req.params;
  console.log(`GET /api/chats/:session_id called with:`, session_id);
  try {
    const session = await Session.findOne({ session_id });
    if (!session) {
      console.warn('Session not found for session_id:', session_id);
      return res.status(404).json({ error: 'Session not found' });
    }
    const result = {
      session_id: session.session_id,
      messages: session.interactions.flatMap(interaction => [
        {
          sender: 'user',
          text: interaction.prompt,
          time: interaction.prompt_time
        },
        {
          sender: 'ai',
          text: interaction.response,
          time: interaction.response_time
        }
      ])
    };
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// (Removed legacy /api/users endpoint for Google login)

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));
