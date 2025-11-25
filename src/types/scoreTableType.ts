export interface ScoreTableType {
  user: {
    user_code: string;
    full_name: string;
    phone_number: string;
  };
  results: {
    avg_speed?: number;
  }[];
}
