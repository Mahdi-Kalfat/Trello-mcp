import mongoose, { Schema } from 'mongoose';

const eventSchema = new Schema({
    title: { type: String, required: true },
    date: { type: Date, required: true },
    time: { type: String, required: true },
    description: { type: String, default: '' },
    userId: { type: String, required: true },
}, { timestamps: true });

export default mongoose.model('Event', eventSchema);