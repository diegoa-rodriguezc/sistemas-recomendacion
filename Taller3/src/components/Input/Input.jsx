import React, { useState } from 'react';
import './Input.scss';

const Input = ({
	               type = 'text',
	               placeholder,
	               value,
	               onChange,
	               className = '',
	               name,
	               label
               }) => {
	const [showPassword, setShowPassword] = useState(false);
	const isPassword = type === 'password';

	const togglePasswordVisibility = () => {
		setShowPassword(!showPassword);
	};

	return (
		<div className="input-group">
			{label && <label htmlFor={name}>{label}</label>}
			<div className="input-wrapper">
				<input
					id={name}
					type={isPassword && showPassword ? 'text' : type}
					placeholder={placeholder}
					value={value}
					onChange={onChange}
					name={name}
					className={`input ${className} ${isPassword ? 'with-icon' : ''}`}
				/>
				{isPassword && (
					<span
						className="password-toggle"
						onClick={togglePasswordVisibility}
					>
            <span className="material-symbols-outlined">
              {showPassword ? 'visibility_off' : 'visibility'}
            </span>
          </span>
				)}
			</div>
		</div>
	);
};

export default Input;