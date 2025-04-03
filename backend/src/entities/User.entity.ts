import {
    Entity,
    PrimaryGeneratedColumn,
    Column,
    CreateDateColumn,
    UpdateDateColumn,
    Index,
} from 'typeorm';

@Entity('users') // Specifies the table name
export class User {
    @PrimaryGeneratedColumn('uuid') // Auto-generated UUID as primary key
    id!: string;

    @Column({ type: 'varchar', length: 255, unique: true })
    @Index() // Add an index for faster email lookups
    email!: string;

    @Column({ type: 'varchar', length: 100, nullable: true }) // Name can be optional initially
    name!: string | null;

    // Future fields like password hash, provider details etc. can be added here
    // @Column({ type: 'varchar', nullable: true })
    // passwordHash: string | null;

    // @Column({ type: 'varchar', nullable: true })
    // authProvider: string | null; // e.g., 'google', 'microsoft', 'local'

    // @Column({ type: 'text', nullable: true })
    // providerId: string | null; // ID from the external provider

    @CreateDateColumn()
    createdAt!: Date;

    @UpdateDateColumn()
    updatedAt!: Date;
} 