import { Tool } from '../types/calendarTypes';

export const calendarTools: Tool[] = [
    {
        name: 'list_today_events',
        description: 'Lists all events for the current day for a specific user.',
        parameters: {
            type: 'object',
            properties: {
                userId: { type: 'string', description: 'The ID of the user whose events to list' },
            },
            required: ['userId'],
        },
    },
    {
        name: 'list_all_events',
        description: 'Lists all events for a specific user.',
        parameters: {
            type: 'object',
            properties: {
                userId: { type: 'string', description: 'The ID of the user whose events to list' },
            },
            required: ['userId'],
        },
    },
    {
        name: 'add_event',
        description: 'Adds a new event for a specific user.',
        parameters: {
            type: 'object',
            properties: {
                userId: { type: 'string', description: 'The ID of the user adding the event' },
                title: { type: 'string', description: 'The title of the event' },
                date: { type: 'string', description: 'The date of the event (YYYY-MM-DD)' },
                time: { type: 'string', description: 'The time of the event (HH:MM)' },
                description: { type: 'string', description: 'Optional description of the event' },
            },
            required: ['userId', 'title', 'date', 'time'],
        },
    },
    {
        name: 'edit_event',
        description: 'Edits an existing event for a specific user.',
        parameters: {
            type: 'object',
            properties: {
                eventId: { type: 'string', description: 'The ID of the event to edit' },
                userId: { type: 'string', description: 'The ID of the user who owns the event' },
                title: { type: 'string', description: 'The updated title of the event' },
                date: { type: 'string', description: 'The updated date of the event (YYYY-MM-DD)' },
                time: { type: 'string', description: 'The updated time of the event (HH:MM)' },
                description: { type: 'string', description: 'The updated description of the event' },
            },
            required: ['eventId', 'userId'],
        },
    },
    {
        name: 'delete_event',
        description: 'Deletes an event for a specific user.',
        parameters: {
            type: 'object',
            properties: {
                eventId: { type: 'string', description: 'The ID of the event to delete' },
                userId: { type: 'string', description: 'The ID of the user who owns the event' },
            },
            required: ['eventId', 'userId'],
        },
    },
];