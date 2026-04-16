(function () {
    const API_ENDPOINT = '/run';

    const COMMAND_MAP = {
        'move_right()': 'right',
        'move_left()': 'left',
        'move_up()': 'up',
        'move_down()': 'down'
    };

    const LEVEL_SEQUENCES = {
        Level_1: ['right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right'],
        Level_2: ['right', 'right', 'right', 'down', 'down', 'right'],
        Level_3: ['right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right'],
        Level_4: ['right', 'up', 'right', 'right', 'right', 'right', 'down', 'down', 'right', 'right'],
        Level_5: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right', 'right', 'down', 'down', 'right'],
        Level_6: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down'],
        Level_7: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right', 'right', 'down', 'down'],
        Level_8: ['right', 'up', 'right', 'right', 'right', 'right', 'up', 'right', 'right', 'down'],
        Level_9: ['down', 'down', 'right', 'down', 'down', 'up', 'up', 'up', 'up', 'right', 'right', 'down', 'right', 'left', 'left', 'down', 'down', 'down', 'right', 'down', 'down', 'down', 'right', 'right'],
        Level_10: ['down', 'down', 'right', 'down', 'down', 'up', 'up', 'up', 'up', 'right', 'right', 'down', 'right', 'left', 'left', 'down', 'down', 'down', 'right', 'down', 'down', 'down', 'right', 'right', 'down']
    };

    function removeComments(code) {
        return code
            .replace(/\/\/.*$/gm, '')
            .replace(/\/\*[\s\S]*?\*\//g, '');
    }

    function skipWhitespace(code, pos) {
        while (pos < code.length && /\s/.test(code[pos])) {
            pos += 1;
        }
        return pos;
    }

    function skipSemicolon(code, pos) {
        pos = skipWhitespace(code, pos);
        if (pos < code.length && code[pos] === ';') {
            return pos + 1;
        }
        return pos;
    }

    function parseFor(code, pos) {
        const forPattern = /for\s*\(\s*let\s+([A-Za-z_$][\w$]*)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{/y;
        forPattern.lastIndex = pos;
        const match = forPattern.exec(code);

        if (!match) {
            throw new Error('Invalid for-loop syntax at position ' + pos);
        }

        const start = parseInt(match[2], 10);
        const end = parseInt(match[3], 10);
        const repeatCount = Math.max(0, end - start);

        let cursor = forPattern.lastIndex;
        const bodyResult = parseStatements(code, cursor);
        cursor = skipWhitespace(code, bodyResult.pos);

        if (cursor >= code.length || code[cursor] !== '}') {
            throw new Error('Missing closing brace for for-loop starting at position ' + pos);
        }

        return {
            moves: repeatCount > 0 ? Array.from({ length: repeatCount }, function () { return bodyResult.moves; }).flat() : [],
            pos: cursor + 1
        };
    }

    function parseStatements(code, pos) {
        const moves = [];
        let cursor = pos;

        while (true) {
            cursor = skipWhitespace(code, cursor);

            if (cursor >= code.length || code[cursor] === '}') {
                break;
            }

            if (code.startsWith('for', cursor)) {
                const loopResult = parseFor(code, cursor);
                moves.push.apply(moves, loopResult.moves);
                cursor = loopResult.pos;
                continue;
            }

            let matched = false;
            Object.keys(COMMAND_MAP).some(function (token) {
                if (code.startsWith(token, cursor)) {
                    moves.push(COMMAND_MAP[token]);
                    cursor += token.length;
                    cursor = skipSemicolon(code, cursor);
                    matched = true;
                    return true;
                }
                return false;
            });

            if (matched) {
                continue;
            }

            throw new Error('Invalid command or syntax at position ' + cursor);
        }

        return { moves: moves, pos: cursor };
    }

    function validateLocally(code, level) {
        if (!code || !code.trim()) {
            return {
                success: false,
                moves: [],
                message: 'Missing code'
            };
        }

        const cleanedCode = removeComments(code);
        const targetSequence = LEVEL_SEQUENCES[level] || LEVEL_SEQUENCES.Level_1;

        try {
            const parsed = parseStatements(cleanedCode, 0);
            const endPos = skipWhitespace(cleanedCode, parsed.pos);
            if (endPos !== cleanedCode.length) {
                throw new Error('Unexpected code after parsing at position ' + endPos);
            }

            const moves = parsed.moves;
            const correctMoves = [];
            for (let i = 0; i < moves.length; i += 1) {
                if (i < targetSequence.length && moves[i] === targetSequence[i]) {
                    correctMoves.push(moves[i]);
                } else {
                    break;
                }
            }

            if (moves.length === targetSequence.length && moves.every(function (move, i) { return move === targetSequence[i]; })) {
                return {
                    success: true,
                    moves: moves,
                    message: 'Perfect! You reached the treasure with the correct sequence!'
                };
            }

            return {
                success: false,
                moves: correctMoves,
                message: 'Incorrect sequence.'
            };
        } catch (error) {
            return {
                success: false,
                moves: [],
                message: error.message
            };
        }
    }

    async function validate(code, level) {
        const payload = {
            code: code,
            level: level
        };

        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            return {
                success: Boolean(data.success),
                moves: Array.isArray(data.moves) ? data.moves : [],
                message: data.message || 'Validation failed.'
            };
        } catch (error) {
            // Fallback lets levels still run if backend is unavailable.
            return validateLocally(code, level);
        }
    }

    window.GameValidator = {
        validate: validate
    };
})();
