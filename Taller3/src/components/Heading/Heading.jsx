import React from 'react';
import './Heading.scss';

const Heading = ({ level = 1, children, className = '' }) => {
	const HeadingTag = `h${level}`;

	return (
		<HeadingTag className={`heading ${className}`}>
			{children}
		</HeadingTag>
	);
};

export default Heading;