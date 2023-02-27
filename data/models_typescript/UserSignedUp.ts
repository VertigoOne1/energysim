
class UserSignedUp {
  private _email?: string;

  constructor(input: {
    email?: string,
  }) {
    this._email = input.email;
  }

  get email(): string | undefined { return this._email; }
  set email(email: string | undefined) { this._email = email; }
}
export default UserSignedUp;
