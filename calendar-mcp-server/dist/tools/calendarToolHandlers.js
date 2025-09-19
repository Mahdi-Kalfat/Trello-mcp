"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.calendarToolHandlers = void 0;
const Event_1 = __importDefault(require("../models/Event"));
exports.calendarToolHandlers = {
    list_today_events(args) {
        return __awaiter(this, void 0, void 0, function* () {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            const events = yield Event_1.default.find({
                userId: args.userId,
                date: { $gte: today, $lt: tomorrow },
            });
            return events;
        });
    },
    list_all_events(args) {
        return __awaiter(this, void 0, void 0, function* () {
            const events = yield Event_1.default.find({ userId: args.userId });
            return events;
        });
    },
    add_event(args) {
        return __awaiter(this, void 0, void 0, function* () {
            const event = new Event_1.default({
                userId: args.userId,
                title: args.title,
                date: new Date(args.date),
                time: args.time,
                description: args.description || '',
            });
            yield event.save();
            return event;
        });
    },
    edit_event(args) {
        return __awaiter(this, void 0, void 0, function* () {
            const event = yield Event_1.default.findOne({ _id: args.eventId, userId: args.userId });
            if (!event) {
                throw new Error('Event not found or not authorized');
            }
            if (args.title)
                event.title = args.title;
            if (args.date)
                event.date = new Date(args.date);
            if (args.time)
                event.time = args.time;
            if (args.description !== undefined)
                event.description = args.description;
            yield event.save();
            return event;
        });
    },
    delete_event(args) {
        return __awaiter(this, void 0, void 0, function* () {
            const event = yield Event_1.default.findOneAndDelete({ _id: args.eventId, userId: args.userId });
            if (!event) {
                throw new Error('Event not found or not authorized');
            }
            return { message: 'Event deleted' };
        });
    },
};
