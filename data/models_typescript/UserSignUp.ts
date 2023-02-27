
class UserSignUp {
  private _displayName?: string;
  private _email?: string;
  private _reservedPassword?: string;

  constructor(input: {
    displayName?: string,
    email?: string,
    reservedPassword?: string,
  }) {
    this._displayName = input.displayName;
    this._email = input.email;
    this._reservedPassword = input.reservedPassword;
  }

  get displayName(): string | undefined { return this._displayName; }
  set displayName(displayName: string | undefined) { this._displayName = displayName; }

  get email(): string | undefined { return this._email; }
  set email(email: string | undefined) { this._email = email; }

  get reservedPassword(): string | undefined { return this._reservedPassword; }
  set reservedPassword(reservedPassword: string | undefined) { this._reservedPassword = reservedPassword; }
}
export default UserSignUp;
