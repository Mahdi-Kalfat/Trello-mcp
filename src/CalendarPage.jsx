import { useEffect, useState } from 'react';

export default function CalendarPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('http://localhost:3001/api/calendar-events')
      .then(res => res.json())
      .then(data => {
        setEvents(data);
        setLoading(false);
      })
      .catch(err => {
        setError('Failed to load calendar events');
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black via-gray-900 to-black/80 p-8">
      <div className="w-full max-w-3xl bg-black/70 rounded-3xl shadow-2xl p-8 border border-white/10">
        <h1 className="text-3xl font-bold text-white mb-6 text-center">Calendar Events</h1>
        {loading ? (
          <div className="text-white/70 text-center">Loading...</div>
        ) : error ? (
          <div className="text-red-400 text-center">{error}</div>
        ) : events.length === 0 ? (
          <div className="text-white/60 text-center">No events found.</div>
        ) : (
          <ul className="divide-y divide-white/10">
            {events.map((event, idx) => (
              <li key={idx} className="py-4 flex flex-col gap-1">
                <span className="text-lg font-semibold text-purple-300">{event.title}</span>
                <span className="text-white/80">{event.date}</span>
                {event.description && <span className="text-white/60 text-sm">{event.description}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
