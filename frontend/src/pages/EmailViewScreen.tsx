import React from 'react';
import { useParams } from 'react-router-dom';

const EmailViewScreen: React.FC = () => {
  const { id } = useParams<{ id: string }>(); // Example of getting route param

  return (
    <div>
      <h1 className="text-xl font-semibold">Email View Screen</h1>
      <p>Details for email ID: {id}</p>
    </div>
  );
};

export default EmailViewScreen; 