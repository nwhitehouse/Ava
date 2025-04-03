import { Router, Request, Response, RequestHandler, NextFunction } from 'express';

const router = Router();

// Mock data for the dashboard
const mockDashboardData = {
    userName: "Nick",
    urgentEmails: [
        { id: "e1", sender: "K1", subject: "AI metrics", snippet: "Need the latest AI metrics for the Q2 report ASAP..." },
        { id: "e2", sender: "Michael", subject: "Data scientists", snippet: "Following up on our chat about data scientists..." },
        { id: "e3", sender: "Emily", subject: "Legalweek confirm", snippet: "Just need your final confirmation for the Legalweek panel..." },
    ],
    delegatableEmails: [
        { id: "e4", sender: "Support", subject: "FW: Ticket #12345", snippet: "Can you assign this support ticket?" },
        { id: "e5", sender: "HR", subject: "New Starter Onboarding", snippet: "Please schedule onboarding for Jane Doe..." },
    ],
    waitingFor: [
        { id: "p1", name: "Alice", topic: "Project Alpha feedback" },
        { id: "p2", name: "Bob", topic: "Budget approval" },
        { id: "p3", name: "Charlie", topic: "Contract draft" },
        { id: "p4", name: "David", topic: "Server access" },
        { id: "p5", name: "Eve", topic: "Design mockups" },
        { id: "p6", name: "Frank", topic: "Final presentation slides" },
    ],
    meetingsToPrep: [
        { id: "m1", title: "Client Sync - Acme Corp", time: "Tomorrow 10:00 AM" },
        { id: "m2", title: "Team Standup", time: "Tomorrow 9:00 AM" },
        { id: "m3", title: "1:1 with Sarah", time: "Wed 2:00 PM" },
        { id: "m4", title: "Product Roadmap Planning", time: "Thu 11:00 AM" },
    ]
};

// GET /api/mock/dashboard
const getDashboardData: RequestHandler = async (req, res, next: NextFunction): Promise<void> => {
    try {
        // In a real scenario, this would involve fetching/processing data
        // For now, just return the mock data
        res.status(200).json(mockDashboardData);
    } catch (error) {
        console.error("Error fetching mock dashboard data:", error);
        if (!res.headersSent) {
            res.status(500).json({ message: 'Internal Server Error' });
        }
        // next(error);
    }
};

router.get('/dashboard', getDashboardData);

export default router; 