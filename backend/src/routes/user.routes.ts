import { Router, Request, Response, RequestHandler, NextFunction } from 'express';
import { AppDataSource } from '../config/data-source';
import { User } from '../entities/User.entity';

const router = Router();
const userRepository = AppDataSource.getRepository(User);

// POST /api/users - Create a new user
const createUser: RequestHandler = async (req, res, next: NextFunction): Promise<void> => {
    try {
        const { email, name } = req.body;

        if (!email) {
            res.status(400).json({ message: 'Email is required' });
            return;
        }

        // Basic validation (can be expanded)
        if (typeof email !== 'string') {
            res.status(400).json({ message: 'Invalid email format' });
            return;
        }

        // Check if user already exists
        const existingUser = await userRepository.findOneBy({ email });
        if (existingUser) {
            res.status(409).json({ message: 'User with this email already exists' });
            return;
        }

        const newUser = userRepository.create({
            email,
            name: name || null, // Use provided name or null
        });

        await userRepository.save(newUser);

        res.status(201).json(newUser);

    } catch (error) {
        console.error("Error creating user:", error);
        if (!res.headersSent) {
             res.status(500).json({ message: 'Internal Server Error' });
        }
    }
};

// GET /api/users - Get all users
const getUsers: RequestHandler = async (req, res, next: NextFunction): Promise<void> => {
    try {
        const users = await userRepository.find();
        res.status(200).json(users);
    } catch (error) {
        console.error("Error fetching users:", error);
        if (!res.headersSent) {
            res.status(500).json({ message: 'Internal Server Error' });
        }
    }
};

// Mount handlers
router.post('/', createUser);
router.get('/', getUsers);

export default router;
