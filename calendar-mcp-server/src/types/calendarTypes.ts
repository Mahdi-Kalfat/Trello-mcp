export interface Event {
    _id: string;
    title: string;
    date: Date;
    time: string;
    description: string;
    userId: string;
    createdAt: Date;
    updatedAt: Date;
}

export interface Tool {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: { [key: string]: { type: string; description: string } };
        required: string[];
    };
}

export interface ToolCall {
    name: string;
    arguments: { [key: string]: any };
}