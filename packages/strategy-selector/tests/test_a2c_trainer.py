from __future__ import annotations

import unittest

from strategy_selector.a2c_trainer import A2CConfig, A2CTrainer


class TestA2CTrainerGradients(unittest.TestCase):
    def test_positive_advantage_increases_selected_action_probability(self) -> None:
        trainer = A2CTrainer(
            A2CConfig(
                state_dim=2,
                action_dim=3,
                hidden_dim=4,
                actor_lr=0.05,
                critic_lr=0.0,
                entropy_coef=0.0,
                min_episodes_before_active=0,
            ),
            checkpoint_dir="__nonexistent_test_checkpoint__",
        )
        trainer.prev_state = [1.0, 0.5]
        trainer.prev_action_idx = 0
        trainer.prev_critic_value = 0.0
        before = trainer.act(trainer.prev_state, deterministic=True)["probs"][0]

        trainer.step([1.0, 0.5], 0, reward=1.0, done=True)

        after = trainer.act([1.0, 0.5], deterministic=True)["probs"][0]
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
