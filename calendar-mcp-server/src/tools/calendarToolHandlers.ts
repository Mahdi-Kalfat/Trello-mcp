import Event from '../models/Event';
import { ToolCall } from '../types/calendarTypes';

export const calendarToolHandlers = {
    async list_today_events(args: { userId: string }) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        const events = await Event.find({
            userId: args.userId,
            date: { $gte: today, $lt: tomorrow },
        });
        return events;
    },

    async list_all_events(args: { userId: string }) {
        const events = await Event.find({ userId: args.userId });
        return events;
    },

    async add_event(args: { userId: string; title: string; date: string; time: string; description?: string }) {
        const event = new Event({
            userId: args.userId,
            title: args.title,
            date: new Date(args.date),
            time: args.time,
            description: args.description || '',
        });
        await event.save();
        return event;
    },

    async edit_event(args: { eventId: string; userId: string; title?: string; date?: string; time?: string; description?: string }) {
        const event = await Event.findOne({ _id: args.eventId, userId: args.userId });
        if (!event) {
            throw new Error('Event not found or not authorized');
        }
        if (args.title) event.title = args.title;
        if (args.date) event.date = new Date(args.date);
        if (args.time) event.time = args.time;
        if (args.description !== undefined) event.description = args.description;
        await event.save();
        return event;
    },

    async delete_event(args: { eventId: string; userId: string }) {
        const event = await Event.findOneAndDelete({ _id: args.eventId, userId: args.userId });
        if (!event) {
            throw new Error('Event not found or not authorized');
        }
        return { message: 'Event deleted' };
    },
};